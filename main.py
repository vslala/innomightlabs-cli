#!/usr/bin/env python3
from prompt_toolkit import prompt
from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit.styles import Style
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.application import Application
from prompt_toolkit.layout.containers import HSplit, Window
from prompt_toolkit.layout.layout import Layout
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.key_binding import KeyBindings
from rich.console import Console
from rich.panel import Panel
from rich.align import Align
from rich.text import Text

from command_processor import CommandProcessor

history = InMemoryHistory()
console = Console()
processor = CommandProcessor()

def display_banner():
    """Display the welcome banner using Rich"""
    console = Console()

    welcome_panel = Panel(
        "\n[bold cyan]INNOMIGHT LABS CLI[/bold cyan]\n\n" +
        "[italic green]Your AI-powered coding assistant[/italic green]\n",
        border_style="bright_blue",
        title="Welcome",
        title_align="center",
        width=80
    )
    
    console.print(welcome_panel, justify="center")
    console.print("\nType your commands below. Commands start with '/'. Type '/exit' to quit.\n")


def create_keybindings():
    """Create custom key bindings for the prompt"""
    kb = KeyBindings()
    console = Console()

    @kb.add('enter')
    def _(event):
        """Process the input when Enter is pressed"""
        buffer = event.app.current_buffer
        text = buffer.text.strip()

        if text == "/exit":
            console.print("Thank you for using Innomight Labs CLI. Goodbye!", style="bold green")
            # Exit the application completely
            import sys
            sys.exit(0)
            return
        elif text.startswith('/'):
            # Execute the command
            buffer.validate_and_handle()
            result = processor.process_command(text)
            console.print("\n")
            console.print(result)
            return
        else:
            buffer.validate_and_handle()

    @kb.add('c-j')
    def _(event):
        """Add a newline when Shift+Enter is pressed"""
        event.current_buffer.insert_text('\n')

    return kb

def main():
    """Main entry point for the application"""
    display_banner()

    

    while True:
        try:

            console.print("─" * console.width, style="bright_blue")

            user_input = prompt(
                HTML("<prompt>innomight></prompt> "),
                style=Style.from_dict({
                    "": "#ffffff",
                    "prompt": "#00aa00 bold",
                }),
                history=history,
                multiline=True,
                wrap_lines=True,
                prompt_continuation=HTML('  <prompt>...</prompt> '),
                key_bindings=create_keybindings(),
                enable_system_prompt=False,  # Ensures proper handling of cursor keys
                mouse_support=True,          # Enable mouse clicks for cursor positioning
            )
            
        except KeyboardInterrupt:
            console.print("\nOperation cancelled by user", style="yellow")
        except EOFError:
            console.print("\nExiting Innomight Labs CLI...", style="bold green")
            break


if __name__ == "__main__":
    main()