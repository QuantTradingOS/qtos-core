"""
Event types for the event-driven core.

Events are immutable data carriers. The engine and handlers react to them;
they do not contain business logic.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class Event:
    """Base type for all events. Subclass to define event kinds."""

    timestamp: datetime
    payload: Any = None

    def __post_init__(self) -> None:
        if not isinstance(self.timestamp, datetime):
            object.__setattr__(self, "timestamp", datetime.fromisoformat(str(self.timestamp)))
