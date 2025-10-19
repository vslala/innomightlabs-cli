#!/usr/bin/env python3
import io
import os
import datetime
import platform
import subprocess
from pathlib import Path
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
from common.utils import console, read_file, logger
from common.containers import container
import os

from tools.sub_agent_tools import plan_act_observe_subagent
from tools.todo_tool import todo_manager

from PIL import ImageGrab, Image

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


def save_clipboard_image(image_bytes: bytes) -> str:
    """Save clipboard image to .krishna/clipboard_images/ directory.
    
    Args:
        image_bytes: Raw image data as bytes
        
    Returns:
        Path to the saved image file
        
    Raises:
        RuntimeError: If image cannot be saved
    """
    try:
        # Create .krishna/clipboard_images directory if it doesn't exist
        clipboard_dir = Path(".krishna/clipboard_images")
        clipboard_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate timestamp-based filename
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        image_path = clipboard_dir / f"clipboard_{timestamp}.png"
        
        # Save image to file
        with open(image_path, 'wb') as f:
            f.write(image_bytes)
            
        return str(image_path)
        
    except Exception as e:
        raise RuntimeError(f"Error saving clipboard image: {str(e)}")



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
        
        def get_text_from_clipboard() -> str | None:
            """Get text content from clipboard across platforms"""
            try:
                # Try platform-specific text clipboard methods
                if platform.system() == "Darwin":  # macOS
                    result = subprocess.run(
                        ["pbpaste"], 
                        capture_output=True, 
                        text=True, 
                        check=False
                    )
                    if result.returncode == 0 and result.stdout.strip():
                        return result.stdout
                elif platform.system() == "Windows":
                    try:
                        import win32clipboard  # type: ignore
                        win32clipboard.OpenClipboard()
                        try:
                            if win32clipboard.IsClipboardFormatAvailable(win32clipboard.CF_TEXT):
                                data: str = win32clipboard.GetClipboardData(win32clipboard.CF_TEXT)
                                return data
                        finally:
                            win32clipboard.CloseClipboard()
                    except ImportError:
                        pass
                else:  # Linux
                    result = subprocess.run(
                        ["xclip", "-selection", "clipboard", "-o"], 
                        capture_output=True, 
                        text=True, 
                        check=False
                    )
                    if result.returncode == 0 and result.stdout.strip():
                        return result.stdout
            except Exception:
                pass
            return None
            
        def get_image_from_clipboard() -> bytes | None:
            """Get image content from clipboard using PIL ImageGrab across all platforms"""
            try:
                # Use PIL ImageGrab for all platforms - it's cross-platform
                logger.debug("[DEBUG] Checking clipboard for images...", style="dim")
                clipboard_content = ImageGrab.grabclipboard()
                
                if clipboard_content is None:
                    logger.debug("[DEBUG] No image found in clipboard", style="dim")
                    return None
                
                # ImageGrab.grabclipboard() can return Image | list[str] | None
                # We only want Image objects, not list[str] (file paths)
                if isinstance(clipboard_content, list):
                    logger.debug("[DEBUG] Clipboard contains file paths, not image data", style="dim")
                    return None
                    
                # Type guard: at this point clipboard_content should be an Image
                if not hasattr(clipboard_content, 'save'):
                    logger.debug("[DEBUG] Clipboard content is not a valid image", style="dim")
                    return None
                    
                img = clipboard_content  # Now we know it's an Image
                logger.debug(f"[DEBUG] Image found in clipboard: {img.size} pixels, mode: {img.mode}", style="dim green")
                
                # Convert image to bytes
                img_bytes = io.BytesIO()
                
                # Handle different image modes
                if img.mode in ('RGBA', 'LA', 'P'):
                    # Convert to RGB for JPEG compatibility, keep PNG for transparency
                    if img.mode == 'P' and 'transparency' in img.info:
                        img = img.convert('RGBA')
                    img.save(img_bytes, format='PNG')
                else:
                    img.save(img_bytes, format='PNG')
                    
                img_data = img_bytes.getvalue()
                logger.debug(f"[DEBUG] Image converted to {len(img_data)} bytes", style="dim green")
                return img_data
                
            except ImportError as e:
                logger.debug(f"[ERROR] PIL not available: {e}", style="red")
                return None
            except Exception as e:
                logger.debug(f"[ERROR] Failed to get image from clipboard: {e}", style="red")
                return None
        
        # Try text first
        text_content = get_text_from_clipboard()
        if text_content:
            buffer.insert_text(text_content)
            return
            
        # Try image if no text
        image_content = get_image_from_clipboard()
        if image_content:
            try:
                image_path = save_clipboard_image(image_content)
                buffer.insert_text(f"<attached_image>{image_path}</attached_image>")
                logger.debug(f"[DEBUG] Image saved to: {image_path}", style="dim green")
            except Exception as e:
                logger.error(f"[ERROR] Failed to save image: {str(e)}", style="red")
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
