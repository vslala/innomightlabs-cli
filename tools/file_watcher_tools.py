"""File watcher tools for the agent system."""

from typing import List, Optional, Any
from rich.console import Console
from watchdog.events import FileSystemEvent

from common.decorators import Tool
from agents.watcher_agent import WatcherAgent
from common.containers import container
from common.file_watcher.metadata import WatcherMetadata
from tools.file_watcher import file_watcher_manager

console = Console()

# Initialize watcher agent
watcher_agent = WatcherAgent(
    conversation_manager=container.in_memory_sliding_window_conversation_manager(),
    text_embedder=container.text_embedder(),
)


@Tool
def start_file_watcher(
    watch_request: str,
    path: Optional[str] = None,
    patterns: Optional[List[str]] = None,
    ignore_patterns: Optional[List[str]] = None,
    recursive: bool = True,
) -> str:
    """Start a new file watcher based on user requirements.

    Args:
        watch_request: Natural language description of what to watch and do
        path: Specific path to watch (optional, will be analyzed from request if not provided)
        patterns: File patterns to watch (optional, will be analyzed from request)
        ignore_patterns: Patterns to ignore (optional, defaults will be used)
        recursive: Whether to watch subdirectories recursively

    Returns:
        Status message with watcher ID
    """
    try:
        # Analyze the watch request using WatcherAgent
        analysis = watcher_agent.analyze_watch_request(watch_request)

        # Override with explicit parameters if provided
        watch_path = path or (
            analysis.get("paths", ["."])[0] if analysis.get("paths") else "."
        )
        watch_patterns = patterns or analysis.get("patterns", [])
        watch_ignore_patterns = ignore_patterns or analysis.get(
            "ignore_patterns", ["__pycache__/*", ".git/*"]
        )
        watch_recursive = (
            recursive if recursive is not None else analysis.get("recursive", True)
        )
        action_prompt = analysis.get(
            "action_prompt", f"Analyze changes for: {watch_request}"
        )
        description = analysis.get("description", f"Watcher for: {watch_request}")

        # Start the watcher with AI-powered callback
        def ai_callback(metadata: WatcherMetadata, event: FileSystemEvent) -> None:
            """Callback that uses AI to execute actions."""
            from tools.sub_agent_tools import agent  # Import sub-agent

            watcher_agent.execute_action(metadata, event, agent)

        watcher_id = file_watcher_manager.start_watcher(
            path=watch_path,
            patterns=watch_patterns,
            ignore_patterns=watch_ignore_patterns,
            recursive=watch_recursive,
            action_prompt=action_prompt,
            description=description,
            callback=ai_callback,
        )

        return f"Started file watcher {watcher_id}: {description}\nWatching: {watch_path}\nPatterns: {watch_patterns or 'all files'}\nIgnoring: {watch_ignore_patterns}"

    except Exception as e:
        return f"Error starting file watcher: {str(e)}"


@Tool
def stop_file_watcher(watcher_id: str) -> str:
    """Stop a running file watcher.

    Args:
        watcher_id: ID of the watcher to stop

    Returns:
        Status message
    """
    try:
        success = file_watcher_manager.stop_watcher(watcher_id)
        if success:
            return f"Successfully stopped watcher {watcher_id}"
        else:
            return f"Watcher {watcher_id} not found or already stopped"
    except Exception as e:
        return f"Error stopping watcher: {str(e)}"


@Tool
def list_file_watchers() -> str:
    """List all active file watchers.

    Returns:
        Formatted list of active watchers
    """
    try:
        watchers = file_watcher_manager.list_watchers()

        if not watchers:
            return "No active file watchers"

        result = "Active File Watchers:\n\n"
        for watcher in watchers:
            status = "🟢 Active" if watcher.is_active else "🔴 Inactive"
            result += f"**{watcher.watcher_id}** - {status}\n"
            result += f"  📁 Path: {watcher.path}\n"
            result += f"  📋 Description: {watcher.description}\n"
            if watcher.patterns:
                result += f"  🎯 Patterns: {', '.join(watcher.patterns)}\n"
            if watcher.ignore_patterns:
                result += f"  🚫 Ignoring: {', '.join(watcher.ignore_patterns)}\n"
            result += f"  🔄 Recursive: {watcher.recursive}\n"
            result += f"  📅 Created: {watcher.created_at}\n"
            result += (
                f"  ⚡ Action: {watcher.action_prompt[:100]}...\n\n"
                if len(watcher.action_prompt) > 100
                else f"  ⚡ Action: {watcher.action_prompt}\n\n"
            )

        return result

    except Exception as e:
        return f"Error listing watchers: {str(e)}"


@Tool
def get_watcher_info(watcher_id: str) -> str:
    """Get detailed information about a specific watcher.

    Args:
        watcher_id: ID of the watcher

    Returns:
        Detailed watcher information
    """
    try:
        watcher = file_watcher_manager.get_watcher(watcher_id)

        if not watcher:
            return f"Watcher {watcher_id} not found"

        status = "🟢 Active" if watcher.is_active else "🔴 Inactive"
        result = f"**Watcher {watcher.watcher_id}** - {status}\n\n"
        result += f"📁 **Path:** {watcher.path}\n"
        result += f"📋 **Description:** {watcher.description}\n"
        result += f"🔄 **Recursive:** {watcher.recursive}\n"
        result += f"📅 **Created:** {watcher.created_at}\n\n"

        if watcher.patterns:
            result += f"🎯 **File Patterns:**\n"
            for pattern in watcher.patterns:
                result += f"  - {pattern}\n"
            result += "\n"

        if watcher.ignore_patterns:
            result += f"🚫 **Ignore Patterns:**\n"
            for pattern in watcher.ignore_patterns:
                result += f"  - {pattern}\n"
            result += "\n"

        result += f"⚡ **Action Prompt:**\n{watcher.action_prompt}\n"

        return result

    except Exception as e:
        return f"Error getting watcher info: {str(e)}"


# Export all tools
file_watcher_tools = [
    start_file_watcher,
    stop_file_watcher,
    list_file_watchers,
    get_watcher_info,
]
