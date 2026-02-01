"""
Order: executable intent (e.g. derived from a Signal after risk check).

Immutable. The core does not send orders to brokers; it only models them.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from qtos_core.signal import Side


class OrderType(Enum):
    MARKET = "market"
    LIMIT = "limit"


@dataclass(frozen=True)
class Order:
    """An order as seen by the core. No broker ID; no fill state here."""

    symbol: str
    side: Side
    quantity: float
    order_type: OrderType = OrderType.MARKET
    limit_price: float | None = None
    timestamp: datetime | None = None
