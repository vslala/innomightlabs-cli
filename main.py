#!/usr/bin/env python3
from typing import Any
from prompt_toolkit import prompt
from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit.styles import Style
from prompt_toolkit.formatted_text import HTML, FormattedText
from prompt_toolkit.key_binding import KeyBindings
from rich.console import Console
from rich.panel import Panel
from rich.align import Align
from rich.text import Text
from rich.markdown import Markdown

from agents.plan_act_observe_agent.plan_act_observe_agent import PlanActObserveAgent
from command_processor import CommandProcessor
from conversation_manager.sliding_window_conversation_manager import (
    SlidingWindowConversationManager,
)
from text_embedding.ollama_text_embedder import OllamaTextEmbedder
from tools.file_system_tool import fs_find, fs_read, fs_search, fs_tools
from tools.shell_tool import shell_command
from common.utils import console, read_file
from common.containers import container
import os

from tools.sub_agent_tools import plan_act_observe_subagent
from tools.todo_tool import todo_manager

os.makedirs(".krishna", exist_ok=True)


history = InMemoryHistory()
processor = CommandProcessor()

system_instructions = read_file("prompts/planner_agent_system_instructions.md")
intuitive_knowledge = read_file("prompts/intuitive_knowledge.md")
planner_agent = PlanActObserveAgent(
    system_prompt=system_instructions,
    intuitive_knowledge=intuitive_knowledge,
    conversation_manager=container.persistent_sliding_window_conversation_manager(),
    text_embedder=container.text_embedder(),
    tools=[plan_act_observe_subagent, todo_manager],
)


def build_bottom_toolbar() -> FormattedText:
    """Render session metrics for the bottom toolbar."""
    totals = planner_agent.usage_totals
    last = planner_agent.last_usage

    segments = [
        ("fg:#00ffff", " Session "),
        (
            "default",
            f"total:{totals['total_tokens']} in:{totals['input_tokens']} out:{totals['output_tokens']}  ",
        ),
        ("fg:#ffd166", "Last "),
        (
            "default",
            f"total:{last['total_tokens']} in:{last['input_tokens']} out:{last['output_tokens']}",
        ),
    ]
    return FormattedText(segments)


def display_banner() -> None:
    """Display the welcome banner using Rich"""
    console = Console()

    welcome_panel = Panel(
        "\n[bold cyan]INNOMIGHT LABS CLI[/bold cyan]\n\n"
        + "[italic green]Your AI-powered coding assistant[/italic green]\n",
        border_style="bright_blue",
        title="Welcome",
        title_align="center",
        width=80,
    )

    console.print(welcome_panel, justify="center")
    console.print(
        "\nType your commands below. Commands start with '/'. Type '/exit' to quit.\n"
    )


def create_keybindings() -> KeyBindings:
    """Create custom key bindings for the prompt"""
    kb = KeyBindings()
    console = Console()

    @kb.add("enter")
    def _(event: Any) -> None:
        """Process the input when Enter is pressed"""
        buffer = event.app.current_buffer
        text = buffer.text.strip()

        if text == "/exit":
            console.print(
                "Thank you for using Innomight Labs CLI. Goodbye!", style="bold green"
            )
            import sys

            sys.exit(0)
            return
        elif text.startswith("/"):
            buffer.validate_and_handle()
            result = processor.process_command(text)
            console.print("\n")
            console.print(result)
            return
        else:
            buffer.validate_and_handle()

    @kb.add("c-j")
    def _(event: Any) -> None:
        """Add a newline when Shift+Enter is pressed"""
        event.current_buffer.insert_text("\n")

    return kb


def main() -> None:
    """Main entry point for the application"""
    display_banner()
    key_bindings = create_keybindings()

    while True:
        try:
            console.print("─" * console.width, style="bright_blue")

            user_input = prompt(
                HTML("<prompt>innomight></prompt> "),
                style=Style.from_dict(
                    {
                        "": "#ffffff",
                        "prompt": "#00aa00 bold",
                    }
                ),
                history=history,
                multiline=True,
                wrap_lines=True,
                prompt_continuation=HTML("  <prompt>...</prompt> "),
                key_bindings=key_bindings,
                enable_system_prompt=False,
                mouse_support=True,
                bottom_toolbar=build_bottom_toolbar,
            )

            if user_input.strip().startswith("/"):
                continue

            final_response = planner_agent.send_message(user_input)
            if not final_response:
                console.print("\n[dim]No response generated.[/dim]\n")
            else:
                console.print(Markdown(final_response))

        except KeyboardInterrupt:
            console.print("\nOperation cancelled by user", style="yellow")
        except EOFError:
            console.print("\nExiting Innomight Labs CLI...", style="bold green")
            break


if __name__ == "__main__":
    main()
