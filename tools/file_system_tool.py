from __future__ import annotations

import fnmatch
import os
import re
from pathlib import Path
from typing import Iterable, Literal, Sequence

from common.decorators import Tool


DEFAULT_MAX_OUTPUT_LINES = 120


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
    mode: Literal["append", "overwrite", "insert", "replace"] = "append",
    line_number: int | None = None,
    end_line: int | None = None,
    create_dirs: bool = True,
) -> str:
    """Write or edit a file using line-based operations.

    Args:
        path: Target file path.
        content: Text to write. Multiple lines are supported.
        mode: Editing strategy - append, overwrite, insert, or replace.
        line_number: 1-based line reference for insert/replace modes.
        end_line: Inclusive 1-based end line for replace mode.
        create_dirs: Create parent directories if missing.

    Returns:
        Summary of the change performed or an error message.
    """

    target = Path(path).expanduser()
    if create_dirs:
        target.parent.mkdir(parents=True, exist_ok=True)

    content_lines = content.splitlines()
    if content.endswith("\n"):
        content_lines.append("")

    if mode == "overwrite":
        text = "\n".join(content_lines)
        target.write_text(text, encoding="utf-8")
        return f"Overwrote {target} with {len(content_lines)} line(s)."

    existing_lines = []
    if target.exists():
        existing_text = target.read_text(encoding="utf-8")
        existing_lines = existing_text.split("\n")

    if mode == "append":
        existing_lines.extend(content_lines)
        action_description = "Appended"
    elif mode == "insert":
        if line_number is None:
            return "line_number is required for insert mode."
        index = max(0, min(line_number - 1, len(existing_lines)))
        existing_lines[index:index] = content_lines
        action_description = f"Inserted at line {line_number}"
    elif mode == "replace":
        if line_number is None or end_line is None:
            return "line_number and end_line are required for replace mode."
        if line_number < 1 or end_line < line_number:
            return "Invalid range for replace. Ensure 1 <= line_number <= end_line."
        start_idx = min(len(existing_lines), line_number - 1)
        end_idx = min(len(existing_lines), end_line)
        existing_lines[start_idx:end_idx] = content_lines
        action_description = f"Replaced lines {line_number}-{end_line}"
    else:
        return f"Unsupported mode '{mode}'."

    text = "\n".join(existing_lines)
    target.write_text(text, encoding="utf-8")
    return f"{action_description} {len(content_lines)} line(s) in {target}."


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
        normalized_exts = {ext if ext.startswith('.') else f'.{ext}' for ext in extensions}
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
        depth = 0 if rel_root == Path('.') else len(rel_root.parts)
        if max_depth is not None and depth >= max_depth:
            dirnames[:] = []

        candidates: Iterable[Path]
        file_candidates = [Path(current_root, name) for name in filenames]
        dir_candidates = [Path(current_root, name) for name in dirnames] if include_dirs else []
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
        normalized_exts = {ext if ext.startswith('.') else f'.{ext}' for ext in extensions}
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
