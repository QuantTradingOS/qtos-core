"""
Execution-layer types: order status, portfolio state, executed trade.

Compatible with backtesting Trade shape so Observers can be reused.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any

from qtos_core.signal import Side


class OrderStatusKind(Enum):
    """Status of an order submitted to a broker/adapter."""

    PENDING = "pending"
    FILLED = "filled"
    PARTIALLY_FILLED = "partially_filled"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


@dataclass(frozen=True)
class OrderStatus:
    """Result of submitting an order. Immutable."""

    status: OrderStatusKind
    order_id: str | None = None
    fill_price: float | None = None
    filled_quantity: float = 0.0
    message: str | None = None
    timestamp: datetime | None = None


@dataclass
class PortfolioState:
    """
    Snapshot of portfolio from broker/adapter (cash + positions).
    Same shape as qtos_core.Portfolio for use with strategies and hooks.
    """

    cash: float = 0.0
    positions: dict[str, float] | None = None

    def __post_init__(self) -> None:
        if self.positions is None:
            object.__setattr__(self, "positions", {})

    def position(self, symbol: str) -> float:
        """Quantity held in symbol. 0 if not present."""
        return self.positions.get(symbol, 0.0)


@dataclass(frozen=True)
class ExecutedTrade:
    """
    Record of a filled order. Same shape as backtesting.engine.Trade
    so Observer callables can be reused across backtest and execution.
    """

    symbol: str
    side: Side
    quantity: float
    price: float
    timestamp: datetime
    order_id: str | None = None
