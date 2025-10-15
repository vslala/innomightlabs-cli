import os
import json
import subprocess
import shutil
from typing import Generator, Optional
from pathlib import Path
from rich.console import Console
from rich.prompt import Prompt
from loguru import logger

# Get the project root directory relative to this file
# This works both in development and PyInstaller bundles
ROOT = Path(__file__).parent.parent.resolve()
console = Console()

log_format = "<green>{time:YYYY-MM-DD HH:mm:ss.SSS zz}</green> | <level>{level: <8}</level> | <yellow>Line {line: >4} ({file}):</yellow> <b>{message}</b>"
logger.add(
    ".krishna/debug.log",
    level="DEBUG",
    format=log_format,
    colorize=False,
    backtrace=True,
    diagnose=True,
)
logger.add(
    ".krishna/info.log",
    level="INFO",
    format=log_format,
    colorize=False,
    backtrace=True,
    diagnose=True,
)


def tree(
    path: str = ".", depth: Optional[int] = None, prefix: str = ""
) -> Generator[str, None, None]:
    if depth is not None and depth < 0:
        return
    entries = sorted(os.listdir(path))
    for i, entry in enumerate(entries):
        full_path = os.path.join(path, entry)
        connector = "└── " if i == len(entries) - 1 else "├── "
        yield (prefix + connector + entry)
        if os.path.isdir(full_path):
            extension = "    " if i == len(entries) - 1 else "│   "
            if depth is None or depth > 0:
                tree(
                    full_path, None if depth is None else depth - 1, prefix + extension
                )


def last_commits(n: int = 5) -> str:
    if shutil.which("git") is None:
        return "Git is not installed or not found in PATH."

    cmd = ["git", "log", f"-n{n}", "--pretty=format:%h | %an | %ar | %s"]
    out = subprocess.check_output(cmd, text=True)
    return out.strip()


def extract_json_from_text(text: str) -> str:
    """Extract the JSON snippet enclosed within a fenced ```json code block.

    Given the text in the following format:

    ```json
    {
        "key": "value"
    }
    ```

    This method extracts the json string and returns it, e.g.:
    {
        "key": "value"
    }

    Args:
        text (str): The input text containing a JSON object.

    Returns:
        str: The JSON string found inside the fenced block, or an empty
            string when the block is not present.
    """

    decoder = json.JSONDecoder()
    search_start = 0

    while True:
        brace_index = text.find("{", search_start)
        if brace_index == -1:
            return ""

        fragment = text[brace_index:]
        stripped_fragment = fragment.lstrip()
        offset = len(fragment) - len(stripped_fragment)
        absolute_start = brace_index + offset

        try:
            _, end_index = decoder.raw_decode(text[absolute_start:])
        except json.JSONDecodeError:
            search_start = brace_index + 1
            continue

        absolute_end = absolute_start + end_index
        return text[absolute_start:absolute_end].strip()


def extract_user_facing_text(raw_reply: str, action_json: str | None) -> str:
    if not raw_reply:
        return ""

    remainder = raw_reply
    if action_json:
        idx = remainder.find(action_json)
        if idx != -1:
            remainder = remainder[:idx] + remainder[idx + len(action_json) :]
        else:
            remainder = remainder.replace(action_json, "", 1)

    cleaned = remainder.replace("```json", "").replace("```", "").strip()
    return cleaned


def read_file(path: str) -> str:
    """Read a file with package-relative path resolution.
    
    This function supports both absolute paths and relative paths.
    Relative paths are resolved relative to the project root directory.
    This works both in development and when bundled with PyInstaller.
    
    Args:
        path (str): File path, can be relative to project root or absolute
        
    Returns:
        str: Contents of the file
        
    Raises:
        FileNotFoundError: If the file cannot be found
        IOError: If the file cannot be read
    """
    file_path = Path(path)
    
    # If it's already an absolute path, use it as-is
    if file_path.is_absolute():
        resolved_path = file_path
    else:
        # Resolve relative to project root
        resolved_path = ROOT / path
    
    try:
        with open(resolved_path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        # Try fallback: resolve relative to current working directory
        # This helps with backward compatibility
        fallback_path = Path.cwd() / path
        if fallback_path.exists():
            with open(fallback_path, "r", encoding="utf-8") as f:
                return f.read()
        raise FileNotFoundError(f"File not found: {path} (tried {resolved_path} and {fallback_path})")



def write_file(path: str, content: str) -> None:
    """Write a file to the .krishna directory with package-relative path resolution.
    
    Args:
        path (str): File path relative to .krishna directory
        content (str): Content to write to the file
    """
    krishna_dir = ROOT / ".krishna"
    krishna_dir.mkdir(exist_ok=True)
    
    file_path = krishna_dir / path
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)
