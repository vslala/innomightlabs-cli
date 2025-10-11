import json
import os
from typing import Any, AsyncGenerator
from uuid import uuid4
from langchain_aws import ChatBedrockConverse
from pydantic import ValidationError
from rich.console import Console
from rich.prompt import Prompt
from rich.markdown import Markdown

from agents.base_agent import BaseAgent
from agents.plan_act_observe_agent.plan_act_observe_agent_model import Action, ActionPlan
from common.models import BaseTool, Message
from common.utils import extract_json_from_text, extract_user_facing_text, tree, last_commits, write_file
from conversation_manager.base_conversation_manager import BaseConversationManager
from text_embedding.base_text_embedder import BaseTextEmbedder
# from agents.krishna_agent.actions import hook_actions



MAX_AGENT_LOOPS = 28
console = Console()
prompt = Prompt()


class PlanActObserveAgent(BaseAgent):
    def __init__(
        self,
        system_prompt: str,
        intuitive_knowledge: str,
        conversation_manager: BaseConversationManager,
        text_embedder: BaseTextEmbedder,
        tools: list[BaseTool] | None = None,
    ) -> None:
        self.llm = ChatBedrockConverse(
            model="us.anthropic.claude-sonnet-4-20250514-v1:0",
            region_name="us-east-1",
            max_tokens=4096,
            credentials_profile_name=os.getenv("AWS_PROFILE", "searchexpert"),
        )
        self.system_prompt = system_prompt
        self.intuitive_knowledge = intuitive_knowledge
        self.conversation_manager = conversation_manager
        self.text_embedder = text_embedder

        self.tools = list(tools or [])

        self.usage_totals: dict[str, int] = {
            "input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0,
        }
        self.last_usage: dict[str, int] = {
            "input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0,
        }
        self.currently_executing: str | None = "None"
        self.user_choices: dict[str, Any] = {}

        

    async def stream(self, prompt: Any) -> AsyncGenerator[str, None]:
        yield "Streaming response part 1..."
        yield "Streaming response part 2..."

    def _update_usage_metrics(self, agent_message: Any) -> None:
        usage = getattr(agent_message, "usage_metadata", None)
        if isinstance(usage, dict):
            input_tokens = int(
                usage.get("input_tokens") or usage.get("prompt_tokens") or 0
            )
            output_tokens = int(
                usage.get("output_tokens") or usage.get("completion_tokens") or 0
            )
            total_tokens = int(
                usage.get("total_tokens") or (input_tokens + output_tokens)
            )

            self.last_usage = {
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": total_tokens,
            }

            self.usage_totals["input_tokens"] += input_tokens
            self.usage_totals["output_tokens"] += output_tokens
            self.usage_totals["total_tokens"] += total_tokens


    
    def send_message(self, user_message: str) -> str:
        """Main loop driving agent/tool interaction for a user request."""
        agent_iterations = 0
        system_instructions = self.system_prompt
        intuitive_knowledge = self.intuitive_knowledge
        self.conversation_manager.add_message(Message(role=f"user", content=user_message, embedding=self.text_embedder.embed_text(user_message)))
        
        tools_blob = "\n".join(tool.model_dump_json() for tool in self.tools)
        plan_example = ActionPlan(
            plan=[
                Action(
                    thought="I should understand the project structure",
                    tool=BaseTool(
                        tool_name="fs_read",
                        tool_params={"path": "path/to/readme.md"},
                    ),
                ),
                Action(
                    thought="I should check the main project file",
                    tool=BaseTool(
                        tool_name="fs_read",
                        tool_params={"path": "path/to/main.py"},
                    ),
                ),
            ]
        ).model_dump_json()
        directory_structure = "\n".join(tree())
        commits = last_commits(7)

        replacements = {
            "{{tools}}": tools_blob,
            "{{plan_generation_example}}": plan_example,
            "{{current_directory_structure}}": directory_structure,
            "{{recent_commits}}": commits,
            "{{current_user_message}}": user_message,
            "{{iteration_count}}": str(agent_iterations)
        }

        intuitive_template = intuitive_knowledge
        for placeholder, value in replacements.items():
            intuitive_template = intuitive_template.replace(placeholder, value)
        
        last_observation = "None"
        final_output = ""
        while True:
            agent_iterations += 1
            try:
                conversation_history = "\n".join(
                    json.dumps({"role": msg.role, "content": msg.content})
                    for msg in self.conversation_manager.fetch_conversation()
                )
                rendered_intuitive = intuitive_template.replace(
                    "{{conversation_history}}", conversation_history
                ).replace("{{last_observation}}", last_observation or "")

                prompt = system_instructions + rendered_intuitive
                write_file("prompt.md", prompt)
                with console.status(":brain: Thinking...", spinner="dots") as status:
                    agent_response = self.llm.invoke(prompt)
                    self._update_usage_metrics(agent_message=agent_response)
                
                if isinstance(agent_response.content, str):
                    plan_or_text = agent_response.content
                    plan = extract_json_from_text(plan_or_text)
                    response = extract_user_facing_text(plan_or_text, plan)
                    self.conversation_manager.add_message(Message(role="assistant", content=response, embedding=self.text_embedder.embed_text(response)))
                    console.print(Markdown(response))
                    
                    if plan:
                        action_plan = ActionPlan.model_validate_json(plan)
                        for action in action_plan.plan:
                            selected_tool = list(filter(lambda t: t.tool_name == action.tool.tool_name, self.tools))
                            if selected_tool:
                                console.print(f"\n[bold]{action.thought}[/bold]")
                                user_response = self._ask_approval(action=action)
                                if isinstance(user_response, str):
                                    self.conversation_manager.add_message(Message(role=f"user", content=user_response, embedding=self.text_embedder.embed_text(user_response)))
                                elif user_response:
                                    tool_response = selected_tool[0].func(**action.tool.tool_params)
                                    tool_use_id = uuid4()
                                    last_observation += f"\nTool Use ID: {tool_use_id}\n{tool_response}\n\n"
                                    self.conversation_manager.add_message(Message(role=f"tool_use[ID={tool_use_id}]", content=tool_response, embedding=self.text_embedder.embed_text(tool_response)))
                                    console.log(f"\n[dim]{tool_response}[/dim]")
                                else:
                                    self.conversation_manager.add_message(Message(role=f"tool_use[tool_name={action.tool.tool_name} ID={uuid4()}]", content="User denied tool execution."))
                                    continue
                    else:
                        self.conversation_manager.finalize()
                        final_output = response
                        break
            except ValidationError as e:
                self.conversation_manager.add_message(Message(role=f"user", content="Validation Error! Provider a plan in proper json format."))
        
        return final_output

    def _ask_approval(self, action: Action) -> bool | str:
        from prompt_toolkit.shortcuts import choice

        tool_params = action.tool.tool_params
        tool_name = action.tool.tool_name

        if self.user_choices.get(tool_name):
            return True

        result = choice(
            message=f"Agent wants to execute a tool: {tool_name}({tool_params}). Do you approve?",
            options=[
                ("y", "Approve"),
                ("n", "Deny"),
                ("s", "Approve and remember my choice for this session"),
                ("c", "Deny and tell what to do")
            ],
            default="n",
        )

        if result == "y":
            return True
        elif result == "s":
            self.user_choices[f"{tool_name}"] = True
            return True
        elif result == "c":
            user_correction = prompt.ask("Tell agent what to do: ")
            return user_correction
        else:
            return False
