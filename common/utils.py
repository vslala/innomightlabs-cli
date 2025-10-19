import os
import json
import subprocess
import shutil
import io
import datetime
import platform
from typing import Generator, Optional
from pathlib import Path
from rich.console import Console
from rich.prompt import Prompt
from loguru import logger
try:
    from PIL import ImageGrab, Image
except ImportError:
    ImageGrab = None  # type: ignore
    Image = None  # type: ignore

__all__ = [
    "ROOT",
    "console", 
    "logger",
    "tree",
    "last_commits",
    "extract_json_from_text",
    "extract_user_facing_text",
    "read_file",
    "write_file",
    "ClipboardManager"
]

# Get the project root directory relative to this file
# This works both in development and PyInstaller bundles
ROOT = Path(__file__).parent.parent.resolve()
console = Console()

# Remove Loguru's default stdout sink to prevent terminal output
logger.remove()

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
    
    try:
        cmd = ["git", "log", f"-n{n}", "--pretty=format:%h | %an | %ar | %s"]
        out = subprocess.check_output(cmd, text=True, stderr=subprocess.DEVNULL)
        return out.strip()
    except subprocess.CalledProcessError:
        return "Not in a git repository or no commits found."


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



class ClipboardManager:
    """Cross-platform clipboard management utility class."""
    
    @staticmethod
    def get_text() -> str | None:
        """Get text content from clipboard across platforms.
        
        Returns:
            str | None: Text content from clipboard or None if no text found
        """
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
        except Exception as e:
            logger.debug(f"Failed to get text from clipboard: {e}")
        return None
    
    @staticmethod
    def get_image() -> bytes | None:
        """Get image content from clipboard using PIL ImageGrab across all platforms.
        
        Returns:
            bytes | None: Image data as bytes or None if no image found
        """
        if ImageGrab is None or Image is None:
            logger.debug("PIL not available for clipboard image operations")
            return None
            
        try:
            logger.debug("Checking clipboard for images...", extra={"markup": True})
            clipboard_content = ImageGrab.grabclipboard()
            
            if clipboard_content is None:
                logger.debug("No image found in clipboard")
                return None
            
            # ImageGrab.grabclipboard() can return Image | list[str] | None
            # We only want Image objects, not list[str] (file paths)
            if isinstance(clipboard_content, list):
                logger.debug("Clipboard contains file paths, not image data")
                return None
                
            # Type guard: at this point clipboard_content should be an Image
            if not hasattr(clipboard_content, 'save'):
                logger.debug("Clipboard content is not a valid image")
                return None
                
            img = clipboard_content  # Now we know it's an Image
            logger.debug(f"Image found in clipboard: {img.size} pixels, mode: {img.mode}")
            
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
            logger.debug(f"Image converted to {len(img_data)} bytes")
            return img_data
            
        except ImportError as e:
            logger.debug(f"PIL not available: {e}")
            return None
        except Exception as e:
            logger.debug(f"Failed to get image from clipboard: {e}")
            return None
    
    @staticmethod
    def save_image(image_bytes: bytes) -> str:
        """Save clipboard image bytes to filesystem.
        
        Args:
            image_bytes: Raw image data as bytes
            
        Returns:
            str: Path to saved image file
            
        Raises:
            RuntimeError: If image save fails
        """
        try:
            # Create clipboard images directory
            clipboard_dir = ROOT / ".krishna" / "clipboard_images"
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
