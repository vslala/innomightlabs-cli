#!/usr/bin/env python3
import os
import subprocess
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
import ollama
from tools.file_system_tool import fs_find, fs_read, fs_search, fs_tools
from tools.shell_tool import shell_command
from common.utils import console, read_file, logger, ClipboardManager
from common.containers import container

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


import os
import datetime
from pathlib import Path



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

    # Add keybinding for newlines
    @kb.add("c-j")
    def _(event: Any) -> None:
        """Add a newline when Shift+Enter is pressed"""
        event.current_buffer.insert_text("\n")
            
    @kb.add("c-v")  # Ctrl+V for Windows/Linux (and fallback for macOS)
    def _(event: Any) -> None:
        """Handle clipboard paste - prioritize text, fallback to images"""
        _handle_paste(event)
    
    def _handle_paste(event: Any) -> None:
        """Common paste handler for all platforms"""
        buffer = event.app.current_buffer
        
        # Try text first
        text_content = ClipboardManager.get_text()
        if text_content:
            buffer.insert_text(text_content)
            return
            
        # Try image if no text
        image_content = ClipboardManager.get_image()
        if image_content:
            try:
                image_path = ClipboardManager.save_image(image_content)
                buffer.insert_text(f"<attached_image>{image_path}</attached_image>")
                logger.debug(f"Image saved to: {image_path}")
            except Exception as e:
                logger.error(f"Failed to save image: {str(e)}")
            return
            
        # No content found
        console.print("No text or image content found in clipboard", style="yellow")
    
    
    return kb


def main() -> None:
    """Main function"""
    display_banner()
    
    style = Style.from_dict({
        'prompt': '#00ff00 bold',
        'response': '#ffffff',
    })
    
    # Create key bindings
    bindings = create_keybindings()
    
    while True:
        try:
            user_input = prompt(
                HTML('<ansicyan><b>Krishna></b></ansicyan> '),
                history=history,
                style=style,
                key_bindings=bindings,
                bottom_toolbar=build_bottom_toolbar,
                multiline=True,
                wrap_lines=True,
                mouse_support=True,
            )
            
            user_input = user_input.strip()
            if not user_input:
                continue
                
            console.print("\n")
            result = planner_agent.send_message(user_input)
            console.print(result)
            console.print("\n")
            
        except KeyboardInterrupt:
            console.print("\n\nGoodbye!", style="bold green")
            break
        except EOFError:
            console.print("\n\nGoodbye!", style="bold green")
            break
        except Exception as e:
            console.print(f"\n[red]Error: {str(e)}[/red]\n")


if __name__ == "__main__":
    main()
