"""Metadata models for file watcher system."""

from datetime import datetime, timezone
from typing import List, Optional
from dataclasses import dataclass, field


@dataclass
class WatcherMetadata:
    """Metadata for a file watcher instance."""

    watcher_id: str
    path: str
    description: str
    action_prompt: str
    is_active: bool = False
    patterns: Optional[List[str]] = None
    ignore_patterns: Optional[List[str]] = field(
        default_factory=lambda: ["__pycache__/*", ".git/*"]
    )
    recursive: bool = True
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def __post_init__(self) -> None:
        """Ensure patterns are empty lists if None."""
        if self.patterns is None:
            self.patterns = []
        if self.ignore_patterns is None:
            self.ignore_patterns = ["__pycache__/*", ".git/*"]
