"""Base file watcher manager interface."""

from abc import ABC, abstractmethod
from typing import List, Optional, Callable, Any
from watchdog.events import FileSystemEvent

from .metadata import WatcherMetadata


class BaseFileWatcherManager(ABC):
    """Abstract base class for file watcher managers."""

    @abstractmethod
    def start_watcher(
        self,
        path: str,
        patterns: List[str],
        ignore_patterns: List[str],
        recursive: bool,
        action_prompt: str,
        description: str,
        callback: Callable[[WatcherMetadata, FileSystemEvent], None],
    ) -> str:
        """Start a new file watcher and return its unique ID.

        Args:
            path: Directory path to watch
            patterns: File patterns to include (e.g., ['*.py', '*.md'])
            ignore_patterns: File patterns to ignore (e.g., ['__pycache__/*'])
            recursive: Whether to watch subdirectories recursively
            action_prompt: AI action description for when files change
            description: Human-readable description of the watcher
            callback: Function to call when file events occur

        Returns:
            Unique watcher ID string

        Raises:
            ValueError: If path doesn't exist or parameters are invalid
            RuntimeError: If watcher cannot be started
        """
        pass

    @abstractmethod
    def stop_watcher(self, watcher_id: str) -> bool:
        """Stop a running file watcher.

        Args:
            watcher_id: ID of the watcher to stop

        Returns:
            True if watcher was stopped, False if not found or already stopped
        """
        pass

    @abstractmethod
    def list_watchers(self) -> List[WatcherMetadata]:
        """Get list of all registered watchers.

        Returns:
            List of WatcherMetadata objects for all watchers
        """
        pass

    @abstractmethod
    def get_watcher(self, watcher_id: str) -> Optional[WatcherMetadata]:
        """Get specific watcher by ID.

        Args:
            watcher_id: ID of the watcher to retrieve

        Returns:
            WatcherMetadata object if found, None otherwise
        """
        pass
