#!/usr/bin/env python3
from prompt_toolkit import prompt
from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit.styles import Style
from prompt_toolkit.formatted_text import HTML, FormattedText
from prompt_toolkit.key_binding import KeyBindings
from rich.console import Console
from rich.panel import Panel
from rich.align import Align
from rich.text import Text

from agents.krishna_agent import KrishnaAgent
from command_processor import CommandProcessor
from conversation_manager.sliding_window_conversation_manager import SlidingWindowConversationManager
from tools.file_system_tool import fs_tools

history = InMemoryHistory()
console = Console()
processor = CommandProcessor()
llm = KrishnaAgent(SlidingWindowConversationManager(), tools=fs_tools)


def build_bottom_toolbar() -> FormattedText:
    """Render session metrics for the bottom toolbar."""
    totals = llm.usage_totals
    last = llm.last_usage

    segments = [
        ("fg:#00ffff", " Session "),
        ("default", f"total:{totals['total_tokens']} in:{totals['input_tokens']} out:{totals['output_tokens']}  "),
        ("fg:#ffd166", "Last "),
        ("default", f"total:{last['total_tokens']} in:{last['input_tokens']} out:{last['output_tokens']}")
    ]
    return FormattedText(segments)

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
            import sys
            sys.exit(0)
            return
        elif text.startswith('/'):
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
    key_bindings = create_keybindings()

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
                key_bindings=key_bindings,
                enable_system_prompt=False, 
                mouse_support=True,
                bottom_toolbar=build_bottom_toolbar,
            )


            with console.status("[bold cyan]Thinking...[/]", spinner="dots") as status:
                response_stream = llm.send_message(user_input)
                response_seen = False
                for msg in response_stream:
                    if not msg or not str(msg).strip():
                        continue
                    if not response_seen:
                        status.stop()  # Stop the status to clear the "Thinking..." display
                        response_seen = True
                    console.print(f"\n{msg}\n")

            if not response_seen:
                console.print("\n[dim]No response generated.[/dim]\n")


        except KeyboardInterrupt:
            console.print("\nOperation cancelled by user", style="yellow")
        except EOFError:
            console.print("\nExiting Innomight Labs CLI...", style="bold green")
            break


if __name__ == "__main__":
    main()
