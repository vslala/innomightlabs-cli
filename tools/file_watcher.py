"""File watcher components for the agent system."""

from common.file_watcher.metadata import WatcherMetadata
from common.containers import container

# Create the file watcher manager instance from the container
file_watcher_manager = container.file_watcher_manager()

# Export the components needed by other modules
__all__ = [
    "WatcherMetadata",
    "file_watcher_manager",
]
