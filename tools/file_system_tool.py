from __future__ import annotations

import fnmatch
import os
import re
from pathlib import Path
from typing import Any, Callable, Iterable, Literal, Sequence
from rich.console import Console
from rich.panel import Panel
import difflib

from common.decorators import Tool


DEFAULT_MAX_OUTPUT_LINES = 120


def _show_beautiful_diff(old_content: str, new_content: str, filepath: str) -> None:
    """Display a beautiful diff using rich console formatting."""
    console = Console()

    # Skip diff if contents are identical
    if old_content == new_content:
        return

    # File header with emoji and styling
    console.print()
    console.print(Panel(f"📝 {filepath}", style="bold cyan", expand=False))

    # Generate unified diff
    old_lines = old_content.splitlines(keepends=True) if old_content else []
    new_lines = new_content.splitlines(keepends=True) if new_content else []

    diff_lines = list(
        difflib.unified_diff(
            old_lines,
            new_lines,
            fromfile=f"a/{filepath}",
            tofile=f"b/{filepath}",
            n=3,  # 3 lines of context
        )
    )

    if not diff_lines:
        return

    # Pretty print diff with colors
    for line in diff_lines:
        line = line.rstrip("\n")

        if line.startswith("---"):
            console.print(line, style="bold red")
        elif line.startswith("+++"):
            console.print(line, style="bold green")
        elif line.startswith("@@"):
            console.print(line, style="bold magenta")
        elif line.startswith("-"):
            console.print(line, style="red")
        elif line.startswith("+"):
            console.print(line, style="green")
        else:
            console.print(line, style="dim white")

    console.print()  # Add spacing after diff


def _prepare_content_lines(content: str) -> list[str]:
    """Split content into lines while preserving a trailing newline."""
    lines = content.splitlines()
    if content.endswith("\n"):
        lines.append("")
    return lines


def _split_text_to_lines(text: str) -> list[str]:
    """Convert full text into a list of lines preserving trailing empties."""
    return text.split("\n") if text else []


def _lines_to_text(lines: list[str]) -> str:
    """Join lines into file text using newline separators."""
    return "\n".join(lines)


def _generate_unified_diff(old_text: str, new_text: str, filepath: str) -> str:
    old_lines = old_text.splitlines(keepends=True) if old_text else []
    new_lines = new_text.splitlines(keepends=True) if new_text else []
    diff = list(
        difflib.unified_diff(
            old_lines,
            new_lines,
            fromfile=f"a/{filepath}",
            tofile=f"b/{filepath}",
            n=3,
        )
    )
    return "".join(diff)


def _apply_append(
    target: Path,
    existing_lines: list[str],
    content_lines: list[str],
    **_: Any,
) -> tuple[list[str], str]:
    new_lines = existing_lines + content_lines
    line_count = len(content_lines)
    summary = f"Appended {line_count} line(s) to {target}."
    return new_lines, summary


def _apply_create(
    target: Path,
    existing_lines: list[str],
    content_lines: list[str],
    **_: Any,
) -> tuple[list[str], str]:
    new_lines = content_lines.copy()
    line_count = len(content_lines)
    action = "Replaced" if target.exists() else "Created"
    summary = f"{action} {target} with {line_count} line(s)."
    return new_lines, summary


def _apply_insert(
    target: Path,
    existing_lines: list[str],
    content_lines: list[str],
    *,
    line_number: int | None,
    **_: Any,
) -> tuple[list[str], str]:
    if line_number is None:
        raise ValueError("line_number is required for insert mode.")
    insertion_index = max(0, min(line_number - 1, len(existing_lines)))
    new_lines = existing_lines.copy()
    new_lines[insertion_index:insertion_index] = content_lines
    line_count = len(content_lines)
    summary = f"Inserted {line_count} line(s) at line {line_number} in {target}."
    return new_lines, summary


def _apply_overwrite_unique(
    target: Path,
    existing_lines: list[str],
    content_lines: list[str],
    *,
    old_str: str | None,
    content: str,
    existing_text: str,
    **_: Any,
) -> tuple[list[str], str]:
    if not old_str:
        raise ValueError("overwrite mode requires a non-empty old_str.")
    occurrences = existing_text.count(old_str)
    if occurrences == 0:
        raise ValueError("Provided old_str was not found in the file.")
    if occurrences > 1:
        raise ValueError(
            "Multiple matches found; only a unique matching str is required for overwrite mode."
        )
    replaced_text = existing_text.replace(old_str, content)
    new_lines = _split_text_to_lines(replaced_text)
    summary = f"Overwrote unique match in {target}."
    return new_lines, summary


def _apply_overwrite_range(
    target: Path,
    existing_lines: list[str],
    content_lines: list[str],
    *,
    line_number: int | None,
    end_line: int | None,
    **_: Any,
) -> tuple[list[str], str]:
    if line_number is None or end_line is None:
        raise ValueError(
            "line_number and end_line are required for overwrite_range mode."
        )
    if line_number < 1 or end_line < line_number:
        raise ValueError(
            "Invalid range for overwrite_range. Ensure 1 <= line_number <= end_line."
        )
    start_idx = min(len(existing_lines), line_number - 1)
    end_idx = min(len(existing_lines), end_line)
    new_lines = existing_lines.copy()
    new_lines[start_idx:end_idx] = content_lines
    line_count = len(content_lines)
    summary = f"Overwrote lines {line_number}-{end_line} in {target} with {line_count} line(s)."
    return new_lines, summary


@Tool
def fs_read(
    path: str,
    start_line: int = 1,
    end_line: int | None = None,
    line_range: str | None = None,
    include_line_numbers: bool = True,
    max_lines: int = DEFAULT_MAX_OUTPUT_LINES,
) -> str:
    """Read line-oriented snippets from a file with optional range controls.

    Args:
        path: File to read.
        start_line: 1-based line to start from when line_range is not provided.
        end_line: Inclusive 1-based line to stop at.
        line_range: Optional "start,end" override for quick range selection.
        include_line_numbers: Prepend line numbers to each returned line.
        max_lines: Hard ceiling for lines returned to keep context compact.

    Returns:
        Selected file slice, limited to max_lines entries, or an error message.
    """

    file_path = Path(path).expanduser()
    if not file_path.exists():
        return f"File not found: {file_path}"
    if not file_path.is_file():
        return f"Path is not a file: {file_path}"

    if line_range:
        try:
            start_str, end_str = re.split(r"[,:-]", line_range)
            start_line = int(start_str)
            end_line = int(end_str)
        except Exception:
            return "Invalid line_range. Use 'start,end' with integers."

    start_line = max(1, start_line)
    if end_line is not None and end_line < start_line:
        return "Invalid range: end_line must be greater than or equal to start_line."

    max_lines = max(1, min(max_lines, DEFAULT_MAX_OUTPUT_LINES))

    lines: list[str] = []
    with file_path.open("r", encoding="utf-8", errors="replace") as handle:
        for index, raw_line in enumerate(handle, start=1):
            if index < start_line:
                continue
            if end_line is not None and index > end_line:
                break
            display = raw_line.rstrip("\n")
            if include_line_numbers:
                display = f"{index}: {display}"
            lines.append(display)
            if len(lines) >= max_lines:
                break

    if not lines:
        return "Selected range produced no content."

    if end_line is not None:
        truncated = len(lines) >= max_lines and end_line - start_line + 1 > max_lines
    else:
        truncated = len(lines) >= max_lines

    snippet = "\n".join(lines)
    if truncated:
        snippet += "\n... (output truncated)"
    return snippet


@Tool
def fs_write(
    path: str,
    content: str,
    mode: Literal[
        "create", "append", "overwrite", "insert", "overwrite_range", "replace"
    ] = "append",
    line_number: int | None = None,
    end_line: int | None = None,
    create_dirs: bool = True,
    old_str: str | None = None,
) -> str:
    """Write or edit a file using line-based operations.

    Args:
        path: Target file path.
        content: Text to write. Multiple lines are supported.
        mode: Editing strategy. Accepted values and required parameters:
            - "create": create a new file or replace the file content entirely with `content`.
            - "append": add content to the end of the file, no extra parameters.
            - "insert": insert at a specific location. Requires `line_number` (1-based).
            - "overwrite": replace one unique string. Requires `old_str` exactly as it appears in the file.
              `content` becomes the replacement text.
            - "overwrite_range" / "replace": replace a span of lines. Requires both `line_number` (start) and
              `end_line` (inclusive).
        line_number: 1-based line reference for insert and overwrite_range/replace modes.
        end_line: Inclusive 1-based end line for overwrite_range/replace modes.
        create_dirs: Create parent directories if missing.
        old_str: String to replace in overwrite mode; must uniquely match existing content.

    Usage notes:
        - "overwrite" will raise an error when `old_str` is missing, empty, or matches multiple locations.
        - When updating an existing snippet, read the file first (via `fs_read`) and copy the exact text into `old_str`.
        - Use "replace" only as the alias for "overwrite_range"; both still require `line_number` and `end_line`.

    Examples:
        {"tool": {"tool_name": "fs_write", "tool_params": {"path": "notes.txt", "content": "First line\n", "mode": "create"}}}
        {"tool": {"tool_name": "fs_write", "tool_params": {"path": "notes.txt", "content": "Another\n", "mode": "append"}}}
        {"tool": {"tool_name": "fs_write", "tool_params": {"path": "notes.txt", "content": "Header\n", "mode": "insert", "line_number": 1}}}
        {"tool": {"tool_name": "fs_write", "tool_params": {"path": "config.ini", "content": "timeout=60", "mode": "overwrite", "old_str": "timeout=30"}}}
        {"tool": {"tool_name": "fs_write", "tool_params": {"path": "notes.txt", "content": "A\nB\n", "mode": "overwrite_range", "line_number": 5, "end_line": 6}}}

    Returns:
        Summary of the change performed or an error message.
    """

    target = Path(path).expanduser()
    if create_dirs:
        target.parent.mkdir(parents=True, exist_ok=True)

    strategies: dict[str, Callable[..., tuple[list[str], str]]] = {
        "create": _apply_create,
        "append": _apply_append,
        "insert": _apply_insert,
        "overwrite": _apply_overwrite_unique,
        "overwrite_range": _apply_overwrite_range,
        "replace": _apply_overwrite_range,
    }

    strategy = strategies.get(mode)
    if strategy is None:
        return f"Unsupported mode '{mode}'."

    existing_text = ""
    if target.exists():
        existing_text = target.read_text(encoding="utf-8")

    existing_lines = _split_text_to_lines(existing_text)
    content_lines = _prepare_content_lines(content)

    try:
        new_lines, summary = strategy(
            target,
            existing_lines,
            content_lines,
            line_number=line_number,
            end_line=end_line,
            old_str=old_str,
            content=content,
            existing_text=existing_text,
        )
    except ValueError as exc:
        return str(exc)

    if mode == "replace":
        summary = summary.replace("Overwrote", "Replaced", 1)

    new_text = _lines_to_text(new_lines)

    if new_text == existing_text:
        return "No changes applied; resulting content matches existing file.\nDiff:\n(no diff)"

    target.write_text(new_text, encoding="utf-8")

    diff_text = _generate_unified_diff(existing_text, new_text, str(target))
    if diff_text:
        _show_beautiful_diff(existing_text, new_text, str(target))
        return f"{summary}\n{diff_text}"
    return f"{summary}\nDiff:\n(no diff)"


@Tool
def fs_find(
    name_pattern: str | None = None,
    contains: str | None = None,
    extensions: Sequence[str] | None = None,
    directory: str = ".",
    include_dirs: bool = False,
    use_regex: bool = False,
    case_sensitive: bool = False,
    max_depth: int | None = None,
    max_results: int = 25,
) -> str:
    """Locate files or directories using flexible filters.

    Args:
        name_pattern: Glob or regex pattern applied to the entry name.
        contains: Substring that must appear in the relative path.
        extensions: Optional list of file extensions (".py", "md").
        directory: Search root.
        include_dirs: Whether to include matching directories in results.
        use_regex: Interpret name_pattern as a regex when True.
        case_sensitive: Respect case when matching.
        max_depth: Optional depth limit relative to the search root.
        max_results: Maximum entries to return.

    Returns:
        Enumerated list of matches or an explanatory message.
    """

    root = Path(directory).expanduser()
    if not root.exists():
        return f"Search root not found: {root}"

    max_results = max(1, max_results)

    if extensions:
        normalized_exts = {
            ext if ext.startswith(".") else f".{ext}" for ext in extensions
        }
    else:
        normalized_exts = None

    pattern_norm: str | None = None
    compiled_regex: re.Pattern[str] | None = None
    if name_pattern:
        if use_regex:
            flags = 0 if case_sensitive else re.IGNORECASE
            compiled_regex = re.compile(name_pattern, flags=flags)
        else:
            pattern_norm = name_pattern if case_sensitive else name_pattern.lower()

    contains_norm = None
    if contains:
        contains_norm = contains if case_sensitive else contains.lower()

    matches: list[str] = []

    for current_root, dirnames, filenames in os.walk(root, followlinks=False):
        rel_root = Path(current_root).relative_to(root)
        depth = 0 if rel_root == Path(".") else len(rel_root.parts)
        if max_depth is not None and depth >= max_depth:
            dirnames[:] = []

        candidates: Iterable[Path]
        file_candidates = [Path(current_root, name) for name in filenames]
        dir_candidates = (
            [Path(current_root, name) for name in dirnames] if include_dirs else []
        )
        candidates = file_candidates + dir_candidates

        for candidate in candidates:
            rel_path = candidate.relative_to(root)
            name = candidate.name

            if normalized_exts and candidate.is_file():
                if candidate.suffix not in normalized_exts:
                    continue

            if name_pattern:
                if use_regex:
                    assert compiled_regex is not None
                    if not compiled_regex.search(name):
                        continue
                else:
                    candidate_name = name if case_sensitive else name.lower()
                    if not fnmatch.fnmatch(candidate_name, pattern_norm or "*"):
                        continue

            if contains_norm is not None:
                rel_path_str = str(rel_path)
                rel_compare = rel_path_str if case_sensitive else rel_path_str.lower()
                if contains_norm not in rel_compare:
                    continue

            matches.append(str(rel_path))
            if len(matches) >= max_results:
                break
        if len(matches) >= max_results:
            break

    if not matches:
        return "No matching entries found."

    lines = [f"{idx + 1}. {match}" for idx, match in enumerate(matches)]
    if len(matches) >= max_results:
        lines.append("... (results truncated)")
    return "\n".join(lines)


@Tool
def fs_search(
    pattern: str,
    directory: str = ".",
    file_glob: str | None = None,
    extensions: Sequence[str] | None = None,
    use_regex: bool = False,
    case_sensitive: bool = False,
    max_matches: int = 40,
    before_context: int = 0,
    after_context: int = 0,
) -> str:
    """Search inside files for a pattern with optional context.

    Args:
        pattern: Text or regex to look for.
        directory: Root directory to search.
        file_glob: Optional glob restricting files (e.g. "**/*.py").
        extensions: Optional list of extensions to include.
        use_regex: Treat pattern as regex when True.
        case_sensitive: Respect case when matching.
        max_matches: Upper bound on reported matches.
        before_context: Lines of context to include before each match.
        after_context: Lines of context to include after each match.

    Returns:
        A concise list of matches with line numbers and optional context.
    """

    if not pattern:
        return "Pattern must not be empty."

    root = Path(directory).expanduser()
    if not root.exists():
        return f"Search root not found: {root}"

    max_matches = max(1, min(max_matches, DEFAULT_MAX_OUTPUT_LINES))

    if extensions:
        normalized_exts = {
            ext if ext.startswith(".") else f".{ext}" for ext in extensions
        }
    else:
        normalized_exts = None

    flags = 0 if case_sensitive else re.IGNORECASE
    try:
        matcher = re.compile(pattern if use_regex else re.escape(pattern), flags=flags)
    except re.error as exc:
        return f"Invalid regular expression: {exc.msg}"

    results: list[str] = []

    for path in root.rglob("*"):
        if not path.is_file():
            continue

        if normalized_exts and path.suffix not in normalized_exts:
            continue

        if file_glob and not fnmatch.fnmatch(str(path.relative_to(root)), file_glob):
            continue

        try:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        except Exception:
            continue

        for line_no, line in enumerate(lines, start=1):
            if matcher.search(line):
                start_context = max(0, line_no - 1 - before_context)
                end_context = min(len(lines), line_no + after_context)
                snippet_lines = lines[start_context:end_context]
                snippet = []
                for idx, ctx_line in enumerate(snippet_lines, start=start_context + 1):
                    prefix = "*" if idx == line_no else " "
                    clipped = ctx_line.strip()
                    if len(clipped) > 160:
                        clipped = f"{clipped[:157]}..."
                    snippet.append(f"{prefix}{idx}: {clipped}")

                rel_path = path.relative_to(root)
                results.append(f"{rel_path}\n" + "\n".join(snippet))
                if len(results) >= max_matches:
                    break
        if len(results) >= max_matches:
            break

    if not results:
        return "No matches found."

    output = "\n---\n".join(results)
    if len(results) >= max_matches:
        output += "\n... (matches truncated)"
    return output


fs_tools = [fs_write, fs_read, fs_find, fs_search]
