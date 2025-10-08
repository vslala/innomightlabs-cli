from rich.console import Console
from common.decorators import Tool

console = Console()

@Tool
def send_message(content: str) -> None:
    """
    Sends a message to the user.

    Args:
        content (str): The message content in markdown format.

    Returns:
        None
    """
    console.print(f"{content}")
    
@Tool
def print_message(content: str) -> None:
    """
    Prints a message to the console. 
    Use these styles with `[style]text[/style]`

    ---

    #### **Basic Styles**

    | Style                | Example               | Code                          |
    | -------------------- | --------------------- | ----------------------------- |
    | **Bold**             | **bold text**         | `[bold]text[/bold]`           |
    | *Italic*             | *italic text*         | `[italic]text[/italic]`       |
    | Underline            | <u>underline text</u> | `[underline]text[/underline]` |
    | Strikethrough        | ~~struck text~~       | `[strike]text[/strike]`       |
    | Dim                  | dim text              | `[dim]text[/dim]`             |
    | Reverse (swap fg/bg) | inverted text         | `[reverse]text[/reverse]`     |
    | Blink                | flashing text         | `[blink]text[/blink]`         |
    | Conceal              | (hidden until copy)   | `[conceal]text[/conceal]`     |

    ---

    #### **Colors**

    Rich supports standard + 256 + hex colors.

    | Type            | Example                                               | Code                                     |
    | --------------- | ----------------------------------------------------- | ---------------------------------------- |
    | Named colors    | red, green, blue, yellow, magenta, cyan, white, black | `[red]error[/red]`                       |
    | Bright variants | bright_red, bright_blue, bright_green                 | `[bright_yellow]warning[/bright_yellow]` |
    | Hex colors      | custom shades                                         | `[#ff6b6b]soft red[/#ff6b6b]`            |
    | RGB triplets    | `[rgb(120,200,255)]sky blue[/rgb(120,200,255)]`       |                                          |

    ---

    #### **Background Colors**

    Add `on` + color name or hex.

    | Example           | Code                                  |
    | ----------------- | ------------------------------------- |
    | yellow background | `[on yellow]highlight[/on yellow]`    |
    | hex background    | `[on #202020]dark block[/on #202020]` |

    ---

    #### **Combining Styles**

    Multiple styles chain together with spaces.

    ```
    [bold magenta on black]Important![/bold magenta on black]
    [italic dim cyan]Hint:[/] use --help for options
    ```

    ---

    #### **Special Markup Helpers**

    | Purpose           | Example                        |
    | ----------------- | ------------------------------ |
    | Escaping brackets | `[[` → `[`                     |
    | Auto-reset style  | `[style]text[/]`               |
    | Emphasis chain    | `[bold red underline]alert[/]` |

    ---

    #### **Useful Color Combos**

    | Use Case | Style          |
    | -------- | -------------- |
    | Success  | `bold green`   |
    | Error    | `bold red`     |
    | Warning  | `bold yellow`  |
    | Info     | `cyan`         |
    | Prompt   | `bold magenta` |
    | Neutral  | `dim white`    |

    ---

    Args:
        content (str): The message content in rich.console format.

    Returns:
        None
    """
    console.print(f"{content}")