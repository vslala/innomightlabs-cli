from agents.plan_act_observe_agent.plan_act_observe_agent import PlanActObserveAgent
from common.decorators import Tool
from common.utils import read_file
from tools.file_system_tool import fs_tools
from tools.shell_tool import shell_command

from common.containers import container


system_instructions = read_file("prompts/plan_act_observe_agent_system_instructions.md")
intuitive_knowledge = read_file("prompts/intuitive_knowledge.md")

agent = PlanActObserveAgent(
    system_prompt=system_instructions,
    intuitive_knowledge=intuitive_knowledge,
    conversation_manager=container.in_memory_conversation_manager(),
    text_embedder=container.text_embedder(),
    tools=fs_tools + [shell_command]
)

@Tool
def plan_act_observe_subagent(prompt: str) -> str:
    """This agent is equipped with various tools such as File System Read/Write/Search/Find and Shell
    with the help of which it can perform various tasks and can be used as a handy assistant to accomplish mini-goals.
    It takes a well defined prompt with step by step action and executes them to get the final result.
    The result can also be produced in whatever way is required just by telling the agent what to do.

    Args:
        prompt (str): Well defined set of instructions on the task that needs to be accomplished.

    Returns:
        str: The output of the said task in the format it is asked for
    """
    return agent.send_message(user_message=prompt)
    