import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated, Any, Dict, List, Literal, Optional

from pydantic import Field

from common.decorators import Tool
from common.utils import ROOT

TODO_FILE = f"{ROOT}/.krishna/todos.json"
TodoStatus = Literal["pending", "in_progress", "completed", "cancelled"]
TodoPriority = Literal["low", "medium", "high"]
TodoMode = Literal[
    "create", "complete", "modify_status", "modify_priority", "list", "delete"
]


def _load_todos() -> List[Dict[str, Any]]:
    """Load todos from the JSON file.

    Returns:
        List of todo dictionaries. Returns empty list if file doesn't exist or is invalid.
    """
    try:
        todo_path = Path(TODO_FILE)
        if not todo_path.exists():
            # Create the .krishna directory if it doesn't exist
            todo_path.parent.mkdir(parents=True, exist_ok=True)
            return []

        with open(todo_path, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if not content:
                return []
            loaded_data = json.loads(content)

            # Type validation: ensure it's a list of dictionaries
            if not isinstance(loaded_data, list):
                print(
                    f"Warning: Invalid todos format in {TODO_FILE}: expected list, got {type(loaded_data)}"
                )
                return []

            # Validate each item is a dictionary
            for item in loaded_data:
                if not isinstance(item, dict):
                    print(
                        f"Warning: Invalid todo item in {TODO_FILE}: expected dict, got {type(item)}"
                    )
                    return []

            # Type cast to satisfy mypy
            todos: List[Dict[str, Any]] = loaded_data
            return todos
    except (json.JSONDecodeError, IOError) as e:
        print(f"Warning: Could not load todos from {TODO_FILE}: {e}")
        return []


def _save_todos(todos: List[Dict[str, Any]]) -> None:
    """Save todos to the JSON file.

    Args:
        todos: List of todo dictionaries to save.

    Raises:
        IOError: If the file cannot be written.
        json.JSONEncodeError: If todos cannot be serialized.
    """
    try:
        # Ensure the .krishna directory exists
        todo_path = Path(TODO_FILE)
        todo_path.parent.mkdir(parents=True, exist_ok=True)

        with open(TODO_FILE, "w", encoding="utf-8") as f:
            json.dump(todos, f, indent=2, ensure_ascii=False)
    except (IOError, TypeError) as e:
        raise IOError(f"Failed to save todos to {TODO_FILE}: {e}")


def _find_todo_by_id(
    todos: List[Dict[str, Any]], todo_id: str
) -> Optional[Dict[str, Any]]:
    """Find a todo by its ID or partial ID match.

    Args:
        todos: List of todo dictionaries.
        todo_id: The ID to search for (can be partial).

    Returns:
        Tuple of (todo_dict, exact_match_bool) if found, (None, False) otherwise.
    """
    # Try exact match first
    exact_match = next((todo for todo in todos if todo.get("id") == todo_id), None)
    if exact_match:
        return exact_match

    # Try partial match
    partial_matches = [t for t in todos if t.get("id", "").startswith(todo_id)]
    if len(partial_matches) == 1:
        return partial_matches[0]
    elif len(partial_matches) > 1:
        raise ValueError(f"Multiple todos match '{todo_id}'. Be more specific.")

    return None


def _format_todo(todo: Dict[str, Any]) -> str:
    """Format a single todo for display.

    Args:
        todo: Todo dictionary to format.

    Returns:
        Formatted string representation of the todo.
    """
    status_emoji = {
        "pending": "⏳",
        "in_progress": "🚧",
        "completed": "✅",
        "cancelled": "❌",
    }

    priority_emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}

    status = todo.get("status", "pending")
    priority = todo.get("priority", "medium")

    status_icon = status_emoji.get(status, "⏳")
    priority_icon = priority_emoji.get(priority, "🟡")

    created_at = datetime.fromisoformat(todo.get("created_at", "")).strftime(
        "%Y-%m-%d %H:%M"
    )

    return f"{status_icon}{priority_icon} [{todo.get('id', 'unknown')[:8]}] {todo.get('content', 'No content')} (Created: {created_at})"


@Tool
def todo_manager(
    mode: Annotated[
        str,
        Field(
            description="Operation mode: create, complete, modify_status, modify_priority, list, delete"
        ),
    ],
    content: Annotated[
        Optional[str], Field(description="Todo content for create mode (single todo)")
    ] = None,
    tasks: Annotated[
        Optional[List[str]],
        Field(description="Array of task strings for bulk create mode"),
    ] = None,
    todo_id: Annotated[
        Optional[str], Field(description="Todo ID for modify/delete operations")
    ] = None,
    status: Annotated[
        Optional[str],
        Field(description="Status: pending, in_progress, completed, cancelled"),
    ] = None,
    priority: Annotated[
        Optional[str], Field(description="Priority: low, medium, high")
    ] = None,
    filter_status: Annotated[
        Optional[str], Field(description="Status filter for list mode")
    ] = None,
) -> str:
    """Unified todo management function with comprehensive CRUD operations.

    Args:
        mode: Operation to perform. Valid options:
            - "create": Create new todo
            - "list": List todos (all or filtered)
            - "complete": Mark todo as completed (shortcut)
            - "modify_status": Change todo status
            - "modify_priority": Change todo priority
            - "delete": Remove todo permanently

        content: Todo description text (for single todo creation)
            - Required for: create (when tasks is not provided)
            - Optional for: all other modes
            - Validation: Must be non-empty string when required
            - Note: Either content or tasks must be provided for create mode

        tasks: Array of task strings (for bulk todo creation)
            - Required for: create (when content is not provided)
            - Optional for: all other modes
            - Validation: Must be non-empty array with non-empty strings
            - Note: Creates multiple todos in one operation with same priority

        todo_id: Unique identifier for existing todo
            - Required for: complete, modify_status, modify_priority, delete
            - Optional for: create, list
            - Supports partial ID matching (first 8+ characters)
            - Validation: Must match exactly one existing todo

        status: Todo status value
            - Required for: modify_status
            - Optional for: all other modes
            - Valid values: "pending", "in_progress", "completed", "cancelled"

        priority: Todo priority level
            - Required for: modify_priority
            - Optional for: create (defaults to "medium")
            - Valid values: "low", "medium", "high"

        filter_status: Status filter for listing
            - Required for: none
            - Optional for: list (shows all todos if omitted)
            - Valid values: same as status parameter

    Usage Examples:

        # CREATE - Add single todo
        todo_manager(mode="create", content="Fix login bug")
        todo_manager(mode="create", content="Review PR #123", priority="high")

        # CREATE - Add multiple todos at once
        todo_manager(mode="create", tasks=["Fix login bug", "Review PR #123", "Update docs"])
        todo_manager(mode="create", tasks=["Task 1", "Task 2"], priority="high")

        # LIST - Show todos
        todo_manager(mode="list")  # All todos
        todo_manager(mode="list", filter_status="pending")  # Only pending

        # COMPLETE - Mark as done (shortcut)
        todo_manager(mode="complete", todo_id="a1b2c3d4")  # Full or partial ID

        # MODIFY_STATUS - Change status
        todo_manager(mode="modify_status", todo_id="a1b2c3d4", status="in_progress")
        todo_manager(mode="modify_status", todo_id="a1b2", status="cancelled")

        # MODIFY_PRIORITY - Change priority
        todo_manager(mode="modify_priority", todo_id="a1b2c3d4", priority="high")

        # DELETE - Remove todo
        todo_manager(mode="delete", todo_id="a1b2c3d4")

    Returns:
        str: Operation result message with emojis and formatting:

        Success Examples:
        - "✅ Todo created successfully!\n⏳🟡 [a1b2c3d4] Fix login bug (Created: 2025-01-02 14:30)"
        - "📋 All Todos (3 items):\n\n⏳🔴 [e5f6g7h8] Review PR #123 (Created: 2025-01-02 14:25)"
        - "✅ Todo marked as completed!\nPrevious status: 'pending'\n✅🟡 [a1b2c3d4] Fix login bug"
        - "🗑️ Todo deleted successfully!\nDeleted: ⏳🟡 [a1b2c3d4] Fix login bug"

        Error Examples:
        - "❌ Invalid mode 'invalid'. Valid modes: create, complete, modify_status, modify_priority, list, delete"
        - "❌ Error: Todo content cannot be empty for create mode."
        - "❌ Todo with ID 'xyz123' not found."
        - "❌ Invalid status 'unknown'. Valid options: pending, in_progress, completed, cancelled"

    Parameter Validation:
        - All string parameters are stripped of whitespace
        - Empty strings treated as None for optional parameters
        - Partial todo_id matching requires unique prefix (no ambiguity)
        - Invalid enum values return helpful error messages
        - File I/O errors are caught and reported gracefully

    Notes:
        - Todos are stored in JSON format at ~/.krishna/todos.json
        - Each todo has: id (UUID), content, status, priority, created_at (ISO timestamp)
        - List mode sorts by priority (high→low) then creation date (newest→oldest)
        - Todo IDs are UUIDs but only first 8 chars shown in display
        - Supports partial ID matching for convenience (e.g., "a1b2c3d4" matches "a1b2")
    """
    valid_modes = [
        "create",
        "complete",
        "modify_status",
        "modify_priority",
        "list",
        "delete",
    ]
    valid_statuses = ["pending", "in_progress", "completed", "cancelled"]
    valid_priorities = ["low", "medium", "high"]

    if mode not in valid_modes:
        return f"❌ Invalid mode '{mode}'. Valid modes: {', '.join(valid_modes)}"

    try:
        todos = _load_todos()

        # CREATE MODE
        if mode == "create":
            # Validate input: either content or tasks must be provided
            has_content = content and content.strip()
            has_tasks = tasks and len(tasks) > 0

            if not has_content and not has_tasks:
                return "❌ Error: Either 'content' or 'tasks' must be provided for create mode."

            if has_content and has_tasks:
                return "❌ Error: Provide either 'content' for single todo or 'tasks' for multiple todos, not both."

            # Set default priority if not provided
            todo_priority = priority if priority in valid_priorities else "medium"
            created_todos = []

            # Handle single content creation
            if has_content:
                new_todo = {
                    "id": str(uuid.uuid4()),
                    "content": content.strip() if content else "",
                    "status": "pending",
                    "priority": todo_priority,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }
                todos.append(new_todo)
                created_todos.append(new_todo)

            # Handle multiple tasks creation
            elif has_tasks:
                for task in tasks or []:
                    if not task or not task.strip():
                        return "❌ Error: All tasks must be non-empty strings."

                    new_todo = {
                        "id": str(uuid.uuid4()),
                        "content": task.strip(),
                        "status": "pending",
                        "priority": todo_priority,
                        "created_at": datetime.now(timezone.utc).isoformat(),
                    }
                    todos.append(new_todo)
                    created_todos.append(new_todo)

            _save_todos(todos)

            # Return summary of created todos
            if len(created_todos) == 1:
                return (
                    f"✅ Todo created successfully!\n{_format_todo(created_todos[0])}"
                )
            else:
                formatted_todos = [_format_todo(todo) for todo in created_todos]
                return (
                    f"✅ {len(created_todos)} todos created successfully!\n\n"
                    + "\n".join(formatted_todos)
                )

        # LIST MODE
        elif mode == "list":
            if not todos:
                return "📝 No todos found. Create your first todo to get started!"

            # Filter by status if provided
            if filter_status:
                if filter_status not in valid_statuses:
                    return f"❌ Invalid status filter '{filter_status}'. Valid options: {', '.join(valid_statuses)}"

                filtered_todos = [
                    todo for todo in todos if todo.get("status") == filter_status
                ]

                if not filtered_todos:
                    return f"📝 No todos found with status '{filter_status}'."

                header = f"📋 Todos with status '{filter_status}' ({len(filtered_todos)} items):"
                todos_to_show = filtered_todos
            else:
                header = f"📋 All Todos ({len(todos)} items):"
                todos_to_show = todos

            # Sort by priority (high to low) then by creation date (newest first)
            priority_order = {"high": 0, "medium": 1, "low": 2}
            todos_to_show.sort(
                key=lambda x: (
                    priority_order.get(x.get("priority", "medium"), 1),
                    -int(datetime.fromisoformat(x.get("created_at", "")).timestamp()),
                )
            )

            formatted_todos = [_format_todo(todo) for todo in todos_to_show]

            return f"{header}\n\n" + "\n".join(formatted_todos)

        # All other modes require todos to exist
        if not todos:
            return "📝 No todos found. Create some todos first!"

        # All other modes require todo_id
        if not todo_id or not todo_id.strip():
            return f"❌ Error: Todo ID is required for {mode} mode."

        # Find the todo
        try:
            todo = _find_todo_by_id(todos, todo_id.strip())
            if not todo:
                return f"❌ Todo with ID '{todo_id}' not found."
        except ValueError as e:
            return f"❌ {str(e)}"

        # COMPLETE MODE (shortcut for setting status to completed)
        if mode == "complete":
            old_status = todo.get("status")
            todo["status"] = "completed"
            _save_todos(todos)
            return f"✅ Todo marked as completed!\nPrevious status: '{old_status}'\n{_format_todo(todo)}"

        # MODIFY_STATUS MODE
        elif mode == "modify_status":
            if not status or status not in valid_statuses:
                return f"❌ Invalid status '{status}'. Valid options: {', '.join(valid_statuses)}"

            old_status = todo.get("status")
            todo["status"] = status
            _save_todos(todos)

            return f"✅ Todo status updated from '{old_status}' to '{status}'!\n{_format_todo(todo)}"

        # MODIFY_PRIORITY MODE
        elif mode == "modify_priority":
            if not priority or priority not in valid_priorities:
                return f"❌ Invalid priority '{priority}'. Valid options: {', '.join(valid_priorities)}"

            old_priority = todo.get("priority", "medium")
            todo["priority"] = priority
            _save_todos(todos)

            return f"✅ Todo priority updated from '{old_priority}' to '{priority}'!\n{_format_todo(todo)}"

        # DELETE MODE
        elif mode == "delete":
            todos.remove(todo)
            _save_todos(todos)

            return f"🗑️ Todo deleted successfully!\nDeleted: {_format_todo(todo)}"

        # This should never be reached due to mode validation above, but added for type safety
        else:
            return f"❌ Unhandled mode '{mode}'. This should not happen."

    except Exception as e:
        return f"❌ An error occurred: {str(e)}"


# Export the todo management function
todo_tools = [todo_manager]
