import json
import uuid
from abc import ABC, abstractmethod
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
    "create", "complete", "modify_status", "modify_priority", "list", "delete",
    "bulk_delete", "bulk_complete", "bulk_modify_status", "bulk_modify_priority"
]
VALID_MODES = [
    "create",
    "complete",
    "modify_status",
    "modify_priority",
    "list",
    "delete",
    "bulk_delete",
    "bulk_complete",
    "bulk_modify_status",
    "bulk_modify_priority",
]
VALID_STATUSES = ["pending", "in_progress", "completed", "cancelled"]
VALID_PRIORITIES = ["low", "medium", "high"]


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


def resolve_by_short_or_full_id(
    todos: List[Dict[str, Any]], todo_id: str
) -> Optional[Dict[str, Any]]:
    """Resolve a todo by full UUID, unique prefix, or first segment before the hyphen."""
    found = _find_todo_by_id(todos, todo_id)
    if found:
        return found

    short_matches = [
        item
        for item in todos
        if item.get("id", "").split("-", 1)[0] == todo_id
    ]
    if len(short_matches) > 1:
        raise ValueError(f"Multiple todos match '{todo_id}'. Be more specific.")
    if len(short_matches) == 1:
        return short_matches[0]
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


class TodoTaskModeInterface(ABC):
    """Strategy interface for todo operations."""

    def __init__(
        self,
        *,
        todos: List[Dict[str, Any]],
        mode: str,
        content: Optional[str],
        tasks: Optional[List[str]],
        todo_id: Optional[str],
        todo_ids: Optional[List[str]],
        status: Optional[str],
        priority: Optional[str],
        filter_status: Optional[str],
    ) -> None:
        self.todos = todos
        self.mode = mode
        self.content = content
        self.tasks = tasks
        self.todo_id = todo_id
        self.todo_ids = todo_ids
        self.status = status
        self.priority = priority
        self.filter_status = filter_status

    @staticmethod
    def _strip(value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None

    @abstractmethod
    def validate(self) -> str:
        """Validate input parameters and return an error message or empty string."""

    @abstractmethod
    def execute(self) -> str:
        """Execute the operation and return the result description."""


class CreateTodoTask(TodoTaskModeInterface):
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._created_todos: List[Dict[str, Any]] = []
        self._single_content: Optional[str] = None
        self._task_contents: List[str] = []
        self._todo_priority: str = "medium"

    def validate(self) -> str:
        content_stripped = self._strip(self.content)
        tasks_list = self.tasks if self.tasks is not None else []
        has_content = bool(content_stripped)
        has_tasks = bool(tasks_list)

        if not has_content and not has_tasks:
            return "❌ Error: Either 'content' or 'tasks' must be provided for create mode."

        if has_content and has_tasks:
            return "❌ Error: Provide either 'content' for single todo or 'tasks' for multiple todos, not both."

        self._todo_priority = (
            self.priority if self.priority in VALID_PRIORITIES else "medium"
        )

        if has_content:
            self._single_content = content_stripped
            return ""

        # Validate tasks list
        cleaned_tasks: List[str] = []
        for task in tasks_list:
            task_stripped = self._strip(task)
            if not task or not task_stripped:
                return "❌ Error: All tasks must be non-empty strings."
            cleaned_tasks.append(task_stripped)

        self._task_contents = cleaned_tasks
        return ""

    def execute(self) -> str:
        created_at = datetime.now(timezone.utc).isoformat()
        if self._single_content:
            new_todo = {
                "id": str(uuid.uuid4()),
                "content": self._single_content,
                "status": "pending",
                "priority": self._todo_priority,
                "created_at": created_at,
            }
            self.todos.append(new_todo)
            self._created_todos.append(new_todo)
        else:
            for task_content in self._task_contents:
                new_todo = {
                    "id": str(uuid.uuid4()),
                    "content": task_content,
                    "status": "pending",
                    "priority": self._todo_priority,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }
                self.todos.append(new_todo)
                self._created_todos.append(new_todo)

        _save_todos(self.todos)

        if len(self._created_todos) == 1:
            return (
                f"✅ Todo created successfully!\n{_format_todo(self._created_todos[0])}"
            )

        formatted_todos = [_format_todo(todo) for todo in self._created_todos]
        return (
            f"✅ {len(self._created_todos)} todos created successfully!\n\n"
            + "\n".join(formatted_todos)
        )


class ListTodoTask(TodoTaskModeInterface):
    def validate(self) -> str:
        if not self.todos:
            return "📝 No todos found. Create your first todo to get started!"
        if self.filter_status:
            if self.filter_status not in VALID_STATUSES:
                return (
                    f"❌ Invalid status filter '{self.filter_status}'. "
                    f"Valid options: {', '.join(VALID_STATUSES)}"
                )
        return ""

    def execute(self) -> str:
        if self.filter_status:
            todos_to_show = [
                todo for todo in self.todos if todo.get("status") == self.filter_status
            ]
            if not todos_to_show:
                return f"📝 No todos found with status '{self.filter_status}'."
            header = (
                f"📋 Todos with status '{self.filter_status}' "
                f"({len(todos_to_show)} items):"
            )
        else:
            todos_to_show = self.todos
            header = f"📋 All Todos ({len(todos_to_show)} items):"

        priority_order = {"high": 0, "medium": 1, "low": 2}
        todos_to_show.sort(
            key=lambda x: (
                priority_order.get(x.get("priority", "medium"), 1),
                -int(datetime.fromisoformat(x.get("created_at", "")).timestamp()),
            )
        )

        formatted_todos = [_format_todo(todo) for todo in todos_to_show]
        return f"{header}\n\n" + "\n".join(formatted_todos)


class TodoIdTask(TodoTaskModeInterface, ABC):
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.todo_item: Optional[Dict[str, Any]] = None
        self.todo_identifier: Optional[str] = None

    def validate(self) -> str:
        if not self.todos:
            return "📝 No todos found. Create some todos first!"
        if not self.todo_id or not self.todo_id.strip():
            return f"❌ Error: Todo ID is required for {self.mode} mode."

        identifier = self.todo_id.strip()
        try:
            todo = self.resolve_todo(identifier)
        except ValueError as exc:
            return f"❌ {str(exc)}"

        if not todo:
            return f"❌ Todo with ID '{self.todo_id}' not found."

        self.todo_item = todo
        self.todo_identifier = identifier
        return ""

    def resolve_todo(self, todo_id: str) -> Optional[Dict[str, Any]]:
        return resolve_by_short_or_full_id(self.todos, todo_id)


class CompleteTodoTask(TodoIdTask):
    def execute(self) -> str:
        assert self.todo_item is not None
        old_status = self.todo_item.get("status")
        self.todo_item["status"] = "completed"
        _save_todos(self.todos)
        return (
            f"✅ Todo marked as completed!\nPrevious status: '{old_status}'\n"
            f"{_format_todo(self.todo_item)}"
        )


class ModifyStatusTodoTask(TodoIdTask):
    def validate(self) -> str:
        base_result = super().validate()
        if base_result:
            return base_result
        if not self.status or self.status not in VALID_STATUSES:
            return (
                f"❌ Invalid status '{self.status}'. "
                f"Valid options: {', '.join(VALID_STATUSES)}"
            )
        return ""

    def execute(self) -> str:
        assert self.todo_item is not None and self.status is not None
        old_status = self.todo_item.get("status")
        self.todo_item["status"] = self.status
        _save_todos(self.todos)
        return (
            f"✅ Todo status updated from '{old_status}' to '{self.status}'!\n"
            f"{_format_todo(self.todo_item)}"
        )


class ModifyPriorityTodoTask(TodoIdTask):
    def validate(self) -> str:
        base_result = super().validate()
        if base_result:
            return base_result
        if not self.priority or self.priority not in VALID_PRIORITIES:
            return (
                f"❌ Invalid priority '{self.priority}'. "
                f"Valid options: {', '.join(VALID_PRIORITIES)}"
            )
        return ""

    def execute(self) -> str:
        assert self.todo_item is not None and self.priority is not None
        old_priority = self.todo_item.get("priority", "medium")
        self.todo_item["priority"] = self.priority
        _save_todos(self.todos)
        return (
            f"✅ Todo priority updated from '{old_priority}' to '{self.priority}'!\n"
            f"{_format_todo(self.todo_item)}"
        )


class DeleteTodoTask(TodoIdTask):
    def execute(self) -> str:
        assert self.todo_item is not None
        self.todos.remove(self.todo_item)
        _save_todos(self.todos)
        return f"🗑️ Todo deleted successfully!\nDeleted: {_format_todo(self.todo_item)}"


class BulkTodoIdTask(TodoTaskModeInterface, ABC):
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.found_todos: List[tuple[Dict[str, Any], str]] = []
        self.error_messages: List[str] = []

    def validate(self) -> str:
        if not self.todo_ids or len(self.todo_ids) == 0:
            return f"❌ Error: todo_ids parameter is required and cannot be empty for {self.mode} mode."

        found_todos: List[tuple[Dict[str, Any], str]] = []
        invalid_ids: List[str] = []
        not_found_ids: List[str] = []

        for todo_id_input in self.todo_ids:
            if not todo_id_input or not todo_id_input.strip():
                invalid_ids.append("<empty>")
                continue

            identifier = todo_id_input.strip()
            try:
                todo = self.resolve_todo(identifier)
            except ValueError as exc:
                invalid_ids.append(f"{identifier} ({str(exc)})")
                continue

            if todo:
                found_todos.append((todo, identifier))
            else:
                not_found_ids.append(identifier)

        error_messages: List[str] = []
        if invalid_ids:
            error_messages.append(f"Invalid IDs: {', '.join(invalid_ids)}")
        if not_found_ids:
            error_messages.append(f"Not found: {', '.join(not_found_ids)}")

        if not found_todos:
            if error_messages:
                return f"❌ No valid todos found. {' | '.join(error_messages)}"
            return "❌ No valid todos found."

        self.found_todos = found_todos
        self.error_messages = error_messages
        return ""

    def resolve_todo(self, todo_id: str) -> Optional[Dict[str, Any]]:
        return resolve_by_short_or_full_id(self.todos, todo_id)


class BulkCompleteTodoTask(BulkTodoIdTask):
    def execute(self) -> str:
        success_count = 0
        results: List[str] = []

        for todo, original_id in self.found_todos:
            old_status = todo.get("status")
            todo["status"] = "completed"
            success_count += 1
            results.append(f"  • {_format_todo(todo)} (was: {old_status})")

        _save_todos(self.todos)

        summary = f"✅ Marked {success_count} todo(s) as completed!"
        if self.error_messages:
            summary += f"\n⚠️  Issues: {' | '.join(self.error_messages)}"
        summary += f"\n\nCompleted todos:\n" + "\n".join(results)
        return summary


class BulkDeleteTodoTask(BulkTodoIdTask):
    def resolve_todo(self, todo_id: str) -> Optional[Dict[str, Any]]:
        return resolve_by_short_or_full_id(self.todos, todo_id)

    def execute(self) -> str:
        success_count = 0
        results: List[str] = []

        for todo, original_id in reversed(self.found_todos):
            results.append(f"  • {_format_todo(todo)}")
            self.todos.remove(todo)
            success_count += 1

        _save_todos(self.todos)

        summary = f"🗑️ Deleted {success_count} todo(s)!"
        if self.error_messages:
            summary += f"\n⚠️  Issues: {' | '.join(self.error_messages)}"
        summary += f"\n\nDeleted todos:\n" + "\n".join(reversed(results))
        return summary


class BulkModifyStatusTodoTask(BulkTodoIdTask):
    def validate(self) -> str:
        base_result = super().validate()
        if base_result:
            return base_result
        if not self.status or self.status not in VALID_STATUSES:
            return (
                f"❌ Invalid status '{self.status}'. "
                f"Valid options: {', '.join(VALID_STATUSES)}"
            )
        return ""

    def execute(self) -> str:
        assert self.status is not None
        success_count = 0
        results: List[str] = []

        for todo, original_id in self.found_todos:
            old_status = todo.get("status")
            todo["status"] = self.status
            success_count += 1
            results.append(f"  • {_format_todo(todo)} (was: {old_status})")

        _save_todos(self.todos)

        summary = (
            f"✅ Updated status to '{self.status}' for {success_count} todo(s)!"
        )
        if self.error_messages:
            summary += f"\n⚠️  Issues: {' | '.join(self.error_messages)}"
        summary += f"\n\nUpdated todos:\n" + "\n".join(results)
        return summary


class BulkModifyPriorityTodoTask(BulkTodoIdTask):
    def validate(self) -> str:
        base_result = super().validate()
        if base_result:
            return base_result
        if not self.priority or self.priority not in VALID_PRIORITIES:
            return (
                f"❌ Invalid priority '{self.priority}'. "
                f"Valid options: {', '.join(VALID_PRIORITIES)}"
            )
        return ""

    def execute(self) -> str:
        assert self.priority is not None
        success_count = 0
        results: List[str] = []

        for todo, original_id in self.found_todos:
            old_priority = todo.get("priority", "medium")
            todo["priority"] = self.priority
            success_count += 1
            results.append(f"  • {_format_todo(todo)} (was: {old_priority})")

        _save_todos(self.todos)

        summary = (
            f"✅ Updated priority to '{self.priority}' for {success_count} todo(s)!"
        )
        if self.error_messages:
            summary += f"\n⚠️  Issues: {' | '.join(self.error_messages)}"
        summary += f"\n\nUpdated todos:\n" + "\n".join(results)
        return summary


@Tool
def todo_manager(
    mode: Annotated[
        str,
        Field(
            description="Operation mode: create, complete, modify_status, modify_priority, list, delete, bulk_delete, bulk_complete, bulk_modify_status, bulk_modify_priority"
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
    todo_ids: Annotated[
        Optional[List[str]], Field(description="List of todo IDs for bulk operations")
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
            - Optional for: create, list, bulk operations
            - Supports partial ID matching (first 8+ characters)
            - Validation: Must match exactly one existing todo

        todo_ids: List of todo IDs for bulk operations
            - Required for: bulk_delete, bulk_complete, bulk_modify_status, bulk_modify_priority
            - Optional for: all other modes
            - Supports partial ID matching (first 8+ characters)
            - Validation: Must be non-empty list with valid todo IDs

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
        # BULK OPERATIONS - Work with multiple todos
        todo_manager(mode="bulk_complete", todo_ids=["a1b2c3d4", "e5f6g7h8"])  # Mark multiple as completed
        todo_manager(mode="bulk_delete", todo_ids=["a1b2", "e5f6"])  # Delete multiple todos
        todo_manager(mode="bulk_modify_status", todo_ids=["a1b2c3d4", "e5f6g7h8"], status="in_progress")
        todo_manager(mode="bulk_modify_priority", todo_ids=["a1b2", "e5f6"], priority="high")



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
    if mode not in VALID_MODES:
        return f"❌ Invalid mode '{mode}'. Valid modes: {', '.join(VALID_MODES)}"

    try:
        todos = _load_todos()
        task_classes: Dict[str, type[TodoTaskModeInterface]] = {
            "create": CreateTodoTask,
            "list": ListTodoTask,
            "complete": CompleteTodoTask,
            "modify_status": ModifyStatusTodoTask,
            "modify_priority": ModifyPriorityTodoTask,
            "delete": DeleteTodoTask,
            "bulk_complete": BulkCompleteTodoTask,
            "bulk_delete": BulkDeleteTodoTask,
            "bulk_modify_status": BulkModifyStatusTodoTask,
            "bulk_modify_priority": BulkModifyPriorityTodoTask,
        }

        task_class = task_classes.get(mode)
        if task_class is None:
            return f"❌ Unhandled mode '{mode}'. This mode is not supported."

        task = task_class(
            todos=todos,
            mode=mode,
            content=content,
            tasks=tasks,
            todo_id=todo_id,
            todo_ids=todo_ids,
            status=status,
            priority=priority,
            filter_status=filter_status,
        )

        validation_message = task.validate()
        if validation_message:
            return validation_message

        return task.execute()

    except Exception as e:
        return f"❌ An error occurred: {str(e)}"


# Export the todo management function
todo_tools = [todo_manager]
