"""Concrete implementation of FileWatcherManager using watchdog."""

import fnmatch
import logging
import os
import uuid
from pathlib import Path
from threading import RLock
from typing import Dict, List, Optional, Callable, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from watchdog.observers import Observer
else:
    from watchdog.observers import Observer


from watchdog.events import FileSystemEventHandler, FileSystemEvent

from .base import BaseFileWatcherManager
from .metadata import WatcherMetadata

logger = logging.getLogger(__name__)


class WatcherEventHandler(FileSystemEventHandler):
    """Event handler for file system events."""

    def __init__(
        self,
        metadata: WatcherMetadata,
        callback: Callable[[WatcherMetadata, FileSystemEvent], None],
        patterns: List[str],
        ignore_patterns: List[str],
    ) -> None:
        super().__init__()
        self.metadata = metadata
        self.callback = callback
        self.patterns = patterns or []
        self.ignore_patterns = ignore_patterns or []

    def _should_process_file(self, file_path: str) -> bool:
        """Check if file should be processed based on patterns."""
        file_name = os.path.basename(file_path)
        relative_path = os.path.relpath(file_path, self.metadata.path)

        # Check ignore patterns first
        for ignore_pattern in self.ignore_patterns:
            if fnmatch.fnmatch(file_name, ignore_pattern) or fnmatch.fnmatch(
                relative_path, ignore_pattern
            ):
                return False

        # If no include patterns specified, include all (except ignored)
        if not self.patterns:
            return True

        # Check include patterns
        for pattern in self.patterns:
            if fnmatch.fnmatch(file_name, pattern) or fnmatch.fnmatch(
                relative_path, pattern
            ):
                return True

        return False

    def _handle_event(self, event: FileSystemEvent) -> None:
        """Handle a file system event."""
        try:
            # Skip directory events if we only care about files
            if event.is_directory:
                return

            # Handle both string and bytes paths
            src_path = event.src_path
            if isinstance(src_path, bytes):
                src_path = src_path.decode("utf-8", errors="replace")

            # Check if file matches our patterns
            if not self._should_process_file(src_path):
                return

            logger.info(f"File event detected: {event.event_type} - {src_path}")

            # Invoke callback with metadata and event
            self.callback(self.metadata, event)

        except Exception as e:
            # Handle both string and bytes paths in error logging
            error_path = event.src_path
            if isinstance(error_path, bytes):
                error_path = error_path.decode("utf-8", errors="replace")
            logger.error(f"Error handling file event {error_path}: {e}")

    def on_modified(self, event: FileSystemEvent) -> None:
        """Handle file modification events."""
        self._handle_event(event)

    def on_created(self, event: FileSystemEvent) -> None:
        """Handle file creation events."""
        self._handle_event(event)

    def on_deleted(self, event: FileSystemEvent) -> None:
        """Handle file deletion events."""
        self._handle_event(event)

    def on_moved(self, event: FileSystemEvent) -> None:
        """Handle file move events."""
        self._handle_event(event)


class WatcherInstance:
    """Internal representation of a watcher instance."""

    def __init__(
        self,
        metadata: WatcherMetadata,
        observer: Any,
        event_handler: WatcherEventHandler,
    ) -> None:
        self.metadata = metadata
        self.observer = observer
        self.event_handler = event_handler
        self._is_running = False

    def start(self) -> None:
        """Start the watcher."""
        if not self._is_running:
            self.observer.start()
            self._is_running = True
            self.metadata.is_active = True
            logger.info(
                f"Started watcher {self.metadata.watcher_id} for path {self.metadata.path}"
            )

    def stop(self) -> None:
        """Stop the watcher."""
        if self._is_running:
            self.observer.stop()
            self.observer.join(timeout=5.0)
            self._is_running = False
            self.metadata.is_active = False
            logger.info(f"Stopped watcher {self.metadata.watcher_id}")

    @property
    def is_running(self) -> bool:
        """Check if the watcher is currently running."""
        return self._is_running and self.observer.is_alive()


class WatchdogFileWatcherManager(BaseFileWatcherManager):
    """Concrete implementation using watchdog library."""

    def __init__(self) -> None:
        super().__init__()
        self._watchers: Dict[str, WatcherInstance] = {}
        self._lock = RLock()

    def _cleanup_stopped_watchers(self) -> None:
        """Remove stopped watchers from internal tracking."""
        with self._lock:
            stopped_watchers = [
                watcher_id
                for watcher_id, instance in self._watchers.items()
                if not instance.is_running
            ]
            for watcher_id in stopped_watchers:
                del self._watchers[watcher_id]

    def start_watcher(
        self,
        path: str,
        patterns: Optional[List[str]] = None,
        ignore_patterns: Optional[List[str]] = None,
        recursive: bool = True,
        action_prompt: str = "Analyze file changes",
        description: str = "File watcher",
        callback: Optional[Callable[[WatcherMetadata, FileSystemEvent], None]] = None,
    ) -> str:
        """Start a new file watcher."""
        # Validate path
        watch_path = Path(path).resolve()
        if not watch_path.exists():
            raise ValueError(f"Path does not exist: {path}")

        if not watch_path.is_dir():
            raise ValueError(f"Path is not a directory: {path}")

        # Create metadata
        watcher_id = str(uuid.uuid4())[:8]
        metadata = WatcherMetadata(
            watcher_id=watcher_id,
            path=str(watch_path),
            patterns=patterns or [],
            ignore_patterns=ignore_patterns or [],
            recursive=recursive,
            action_prompt=action_prompt,
            description=description,
        )

        # Create observer and event handler
        observer: Any = Observer()

        def default_callback(metadata: WatcherMetadata, event: FileSystemEvent) -> None:
            """Default callback that just logs events."""
            event_path = event.src_path
            if isinstance(event_path, bytes):
                event_path = event_path.decode("utf-8", errors="replace")
            logger.info(f"File {event.event_type}: {event_path}")

        event_handler = WatcherEventHandler(
            metadata=metadata,
            callback=callback or default_callback,
            patterns=patterns or [],
            ignore_patterns=ignore_patterns or [],
        )

        # Schedule the observer
        observer.schedule(event_handler, str(watch_path), recursive=recursive)

        # Create and store watcher instance
        watcher_instance = WatcherInstance(
            metadata=metadata, observer=observer, event_handler=event_handler
        )

        with self._lock:
            self._watchers[watcher_id] = watcher_instance
            watcher_instance.start()

        return watcher_id

    def stop_watcher(self, watcher_id: str) -> bool:
        """Stop a specific watcher."""
        with self._lock:
            if watcher_id not in self._watchers:
                return False

            watcher_instance = self._watchers[watcher_id]
            watcher_instance.stop()
            del self._watchers[watcher_id]

        return True

    def list_watchers(self) -> List[WatcherMetadata]:
        """Get list of all active watchers."""
        self._cleanup_stopped_watchers()

        with self._lock:
            return [instance.metadata for instance in self._watchers.values()]

    def get_watcher(self, watcher_id: str) -> Optional[WatcherMetadata]:
        """Get metadata for a specific watcher."""
        with self._lock:
            instance = self._watchers.get(watcher_id)
            return instance.metadata if instance else None

    def stop_all_watchers(self) -> int:
        """Stop all active watchers."""
        with self._lock:
            count = len(self._watchers)

            for watcher_instance in self._watchers.values():
                watcher_instance.stop()

            self._watchers.clear()

        return count


# Global instance for easy access
file_watcher_manager = WatchdogFileWatcherManager()
