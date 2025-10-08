import json
import os
import textwrap
from typing import Any, AsyncGenerator, Generator

from langchain_aws import ChatBedrockConverse
from pydantic import ValidationError
from rich.console import Console

from agents.base_agent import BaseAgent
from common.models import Action, BaseTool, Message
from common.utils import extract_json_from_text
from conversation_manager.base_conversation_manager import BaseConversationManager
from tools.send_message import print_message, send_message


MAX_AGENT_LOOPS = 28
console = Console()


class KrishnaAgent(BaseAgent):

    def __init__(
        self,
        conversation_manager: BaseConversationManager,
        tools: list[BaseTool] | None = None,
    ) -> None:
        self.llm = ChatBedrockConverse(
            model="us.anthropic.claude-sonnet-4-20250514-v1:0",
            region_name="us-east-1",
            max_tokens=4096,
            credentials_profile_name=os.getenv("AWS_PROFILE", "searchexpert"),
        )
        self.conversation_manager = conversation_manager

        configured_tools = list(tools or [])
        if not any(tool.tool_name == print_message.tool_name for tool in configured_tools):
            configured_tools.append(print_message)
        if not any(tool.tool_name == send_message.tool_name for tool in configured_tools):
            configured_tools.append(send_message)
        self.tools = configured_tools

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

    async def stream(self, prompt: Any) -> AsyncGenerator[str, None]:
        yield "Streaming response part 1..."
        yield "Streaming response part 2..."

    def send_message(self, user_message: str) -> Generator[str, None]:
        self.conversation_manager.add_message(Message(role="user", content=user_message))

        action: Action | None = None
        turn_counter = 0

        while action is None or action.request_heartbeat:
            turn_counter += 1
            if turn_counter > MAX_AGENT_LOOPS:
                failure = "Maximum tool iterations exceeded. Please refine the request."
                self._append_system_message(failure)
                yield failure
                return

            prompt = self.build_prompt(user_message)
            agent_message = self.llm.invoke(prompt)

            usage = getattr(agent_message, "usage_metadata", None)
            if isinstance(usage, dict):
                input_tokens = int(usage.get("input_tokens") or usage.get("prompt_tokens") or 0)
                output_tokens = int(usage.get("output_tokens") or usage.get("completion_tokens") or 0)
                total_tokens = int(usage.get("total_tokens") or (input_tokens + output_tokens))

                self.last_usage = {
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "total_tokens": total_tokens,
                }

                self.usage_totals["input_tokens"] += input_tokens
                self.usage_totals["output_tokens"] += output_tokens
                self.usage_totals["total_tokens"] += total_tokens

            if not isinstance(agent_message.content, str):
                failure = "Model returned a non-textual response. Unable to continue."
                self._append_system_message(failure)
                yield failure
                return

            self.conversation_manager.add_message(
                Message(role="assistant", content=agent_message.content)
            )

            action_json = extract_json_from_text(agent_message.content)
            if not action_json:
                self._append_system_message(
                    "Your previous reply did not include the required JSON action. Respond with valid JSON."
                )
                action = None
                continue

            try:
                action_payload = json.loads(action_json)
            except json.JSONDecodeError as exc:
                self._append_system_message(
                    f"JSON parsing error: {exc.msg}. Provide a valid JSON object in the next message."
                )
                action = None
                continue

            try:
                action = Action.model_validate(action_payload)
            except ValidationError as exc:
                self._append_system_message(
                    "Action schema validation failed. Ensure the response follows the required format."
                )
                console.log(f"[red]{exc}[/red]")
                action = None
                continue

            selected_tool = self._resolve_tool(action.tool.tool_name)
            if selected_tool is None:
                available = ", ".join(tool.tool_name for tool in self.tools)
                self._append_system_message(
                    f"Tool '{action.tool.tool_name}' is unavailable. Choose one of: {available}."
                )
                action = None
                continue

            if not isinstance(action.tool.tool_params, dict):
                self._append_system_message(
                    "tool.tool_params must be an object containing the call arguments."
                )
                action = None
                continue

            if action.tool.tool_params == selected_tool.tool_params:
                self._append_system_message(
                    f"Do not return the parameter schema for '{selected_tool.tool_name}'. Provide actual argument values."
                )
                action = None
                continue

            try:
                tool_response = selected_tool.func(**action.tool.tool_params)
            except TypeError as exc:
                self._append_tool_error(selected_tool.tool_name, f"Invalid arguments: {exc}")
                action = None
                continue
            except Exception as exc:  # pragma: no cover - defensive guard
                self._append_tool_error(selected_tool.tool_name, f"Execution error: {exc}")
                action = None
                continue

            tool_feedback = self._format_tool_feedback(selected_tool, action, tool_response)
            self.conversation_manager.add_message(
                Message(role="tool", content=tool_feedback)
            )

            if selected_tool.tool_name not in {"print_message", "send_message"} and tool_feedback:
                yield tool_feedback

        return

    def persist_conversation(self) -> None:
        self.conversation_manager.persist_conversation()

    def build_prompt(self, user_message: str) -> str:
        tools_block = self._format_tools_for_prompt()
        history_block = self._format_conversation_history()

        prompt = textwrap.dedent(
            f"""
            <base_instructions>
            You are Krishna, a sentient programming assistant. Use the available tools to fulfill the user's request.

            <tooling>
            The following tools can be invoked:
            {tools_block}
            </tooling>

            <response_format>
            - Reply with a single JSON object only (no markdown fences).
            - Shape the response exactly as: {{"tool": {{"tool_name": "<name>", "tool_params": {{...}}}}, "request_heartbeat": <true|false>}}.
            - Include only the chosen tool name and the concrete argument values inside tool_params.
            - Do NOT repeat tool descriptions or parameter schemas in the response.
            - Set request_heartbeat to true only when you must immediately invoke another tool afterwards.
            </response_format>

            Maintain concise reasoning internally; external messages should rely on the send/print message tools.
            </base_instructions>

            <conversation_history>
            {history_block}
            </conversation_history>

            <user_message>
            {user_message}
            </user_message>
            """
        ).strip()

        return prompt

    def _resolve_tool(self, tool_name: str) -> BaseTool | None:
        for tool in self.tools:
            if tool.tool_name == tool_name:
                return tool
        return None

    def _format_tools_for_prompt(self) -> str:
        tool_specs = [
            {
                "tool_name": tool.tool_name,
                "description": tool.description,
                "parameters_schema": tool.tool_params,
            }
            for tool in self.tools
        ]
        return json.dumps(tool_specs, indent=4)

    def _format_conversation_history(self) -> str:
        history = self.conversation_manager.fetch_conversation()
        if not history:
            return "[]"
        return "\n".join(
            json.dumps({"role": msg.role, "content": msg.content}) for msg in history
        )

    def _append_system_message(self, content: str) -> None:
        self.conversation_manager.add_message(Message(role="system", content=content))

    def _append_tool_error(self, tool_name: str, message: str) -> None:
        feedback = f"ERROR[{tool_name}]: {message}"
        self.conversation_manager.add_message(Message(role="tool", content=feedback))

    def _format_tool_feedback(
        self,
        tool: BaseTool,
        action: Action,
        tool_response: Any,
    ) -> str:
        if tool_response is not None:
            return str(tool_response)

        if "content" in action.tool.tool_params:
            return str(action.tool.tool_params["content"])

        return "Tool execution completed."
