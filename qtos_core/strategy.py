"""
Strategy: interface for signal generation.

Strategies consume events and optional state (e.g. portfolio) and produce Signals.
Implementations define the logic; the engine wires events and calls on_event.
"""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from qtos_core.events import Event
    from qtos_core.portfolio import Portfolio
    from qtos_core.signal import Signal


class Strategy(ABC):
    """
    Base class for strategies. Receives events; may emit signals.
    The engine is responsible for passing events and collecting signals.
    """

    @abstractmethod
    def on_event(
        self,
        event: "Event",
        portfolio: "Portfolio | None" = None,
    ) -> list["Signal"]:
        """
        React to an event. Return zero or more signals.
        Portfolio is optional read-only context.
        """
        ...
