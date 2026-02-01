"""
Buy-and-hold example strategy.

Emits a single buy signal for a fixed symbol on the first event it sees.
No sizing logic—minimal illustration of the Strategy interface.
"""

from datetime import datetime

from qtos_core.events import Event
from qtos_core.portfolio import Portfolio
from qtos_core.signal import Signal, Side
from qtos_core.strategy import Strategy


class BuyAndHoldStrategy(Strategy):
    """
    On first event, emit one buy signal for the configured symbol.
    Ignores subsequent events (already “in” the market).
    """

    def __init__(self, symbol: str, quantity: float = 1.0) -> None:
        self.symbol = symbol
        self.quantity = quantity
        self._fired = False

    def on_event(
        self,
        event: Event,
        portfolio: Portfolio | None = None,
    ) -> list[Signal]:
        if self._fired:
            return []
        self._fired = True
        ts = event.timestamp if hasattr(event, "timestamp") else datetime.now()
        return [
            Signal(
                symbol=self.symbol,
                side=Side.BUY,
                quantity=self.quantity,
                timestamp=ts,
            )
        ]
