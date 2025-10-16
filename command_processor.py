"""
Command processor module for Innomight Labs CLI.
Handles parsing and executing user commands.
"""

from agents.plan_act_observe_agent.plan_act_observe_agent import PlanActObserveAgent
from common.utils import read_file
from common.containers import container



class CommandProcessor:
    """
    Processes and executes commands entered by the user in the CLI.
    """

    def __init__(self) -> None:
        self.commands = {
            "/help": self.show_help,
            "/version": self.show_version,
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
/exit      - Exit the CLI application

Usage:
Commands begin with a forward slash (/).

You can enter multi-line text by pressing Enter while typing.
To execute a command, press Enter on a new line.
        """
        return help_text.strip()

    def show_version(self, args: str = "") -> str:
        """Display the current version of the CLI"""
        return "Innomight Labs CLI v0.1.0"


