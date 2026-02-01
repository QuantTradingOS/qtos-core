"""
Signal: trading intent produced by a strategy.

Immutable. No execution—just direction, symbol, and size.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class Side(Enum):
    BUY = "buy"
    SELL = "sell"


@dataclass(frozen=True)
class Signal:
    """Trading intent: what to do, not an order."""

    symbol: str
    side: Side
    quantity: float
    timestamp: datetime
