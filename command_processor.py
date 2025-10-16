"""
Command processor module for Innomight Labs CLI.
Handles parsing and executing user commands.
"""

from agents.plan_act_observe_agent.plan_act_observe_agent import PlanActObserveAgent
from common.utils import read_file
from common.containers import container
from tools.file_watcher_tools import (
    start_file_watcher,
    stop_file_watcher,
    list_file_watchers,
)


class CommandProcessor:
    """
    Processes and executes commands entered by the user in the CLI.
    """

    def __init__(self) -> None:
        self.commands = {
            "/help": self.show_help,
            "/version": self.show_version,
            "/watch": self.watch_command,
        }

    def process_command(self, command_text: str) -> str:
        """
        Process a command string and execute the appropriate action.

        Args:
            command_text (str): The command entered by the user

        Returns:
            str: The result of the command execution
        """
        command_parts = command_text.strip().split(maxsplit=1)
        if not command_parts:
            return ""

        command_name = command_parts[0].lower()
        args = command_parts[1] if len(command_parts) > 1 else ""

        if command_name in self.commands:
            return self.commands[command_name](args)

        return (
            f"Command not found: {command_name}. Type '/help' for available commands."
        )

    def show_help(self, args: str = "") -> str:
        """Display help information about available commands"""
        help_text = """
Available Commands:
------------------
/help      - Show this help message
/version   - Show the current version of Innomight Labs CLI
/watch     - Manage file watchers with natural language requests
/exit      - Exit the CLI application

Usage:
Commands begin with a forward slash (/).
For /watch command, provide natural language requests like:
  /watch Monitor Python files for changes
  /watch Stop all watchers
  /watch List active watchers

You can enter multi-line text by pressing Enter while typing.
To execute a command, press Enter on a new line.
        """
        return help_text.strip()

    def show_version(self, args: str = "") -> str:
        """Display the current version of the CLI"""
        return "Innomight Labs CLI v0.1.0"

    def watch_command(self, args: str = "") -> str:
        """Handle file watcher management using natural language requests"""
        if not args.strip():
            return (
                "Please provide a file watcher request. Examples:\n"
                "- /watch Monitor Python files for changes\n"
                "- /watch List active watchers\n"
                "- /watch Stop watcher abc123"
            )

        try:
            # Load the file watcher system prompt
            system_prompt = read_file(
                "prompts/file_watcher_command_system_instructions.md"
            )

            # Create PlanActObserveAgent with file watcher tools
            agent = PlanActObserveAgent(
                system_prompt=system_prompt,
                intuitive_knowledge="",  # No additional intuitive knowledge needed
                conversation_manager=container.in_memory_sliding_window_conversation_manager(),
                text_embedder=container.text_embedder(),
                tools=[start_file_watcher, stop_file_watcher, list_file_watchers],
            )

            # Process the user request
            result = agent.send_message(args)

            return f"File Watcher Command Result:\n{result}"

        except Exception as e:
            return f"Error processing file watcher command: {str(e)}"
