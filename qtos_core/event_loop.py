"""
Event loop: single-threaded, deterministic event processing.

Dispatches events to registered handlers. No async; order of handlers is explicit.
"""

from collections.abc import Callable
from typing import TypeVar

from qtos_core.events import Event

E = TypeVar("E", bound=Event)


class EventLoop:
    """
    Deterministic event loop. Handlers are called in registration order
    for each event. No broker, no I/O—pure in-memory processing.
    """

    def __init__(self) -> None:
        self._handlers: list[Callable[[Event], None]] = []

    def subscribe(self, handler: Callable[[Event], None]) -> None:
        """Register a handler to be called for every event."""
        self._handlers.append(handler)

    def dispatch(self, event: Event) -> None:
        """Process one event through all handlers in order."""
        for h in self._handlers:
            h(event)

    def run(self, events: list[Event]) -> None:
        """Process a sequence of events in order (e.g. backtest)."""
        for event in events:
            self.dispatch(event)
