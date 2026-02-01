"""
Paper trading adapter: simulates fills in real-time using latest market data.

No broker connection. Maintains internal portfolio state; get_market_data returns
data from a provided source (e.g. dict of symbol -> price, or DataFrame provider).
"""

from __future__ import annotations

from datetime import datetime
from typing import Callable
import uuid

import pandas as pd

from qtos_core.order import Order
from qtos_core.signal import Side

from qtos_core.execution.broker import BrokerAdapter
from qtos_core.execution.types import OrderStatus, OrderStatusKind, PortfolioState


def _default_market_data(symbols: list[str]) -> pd.DataFrame:
    """Default: no data. Override via constructor for paper simulation."""
    return pd.DataFrame(columns=["symbol", "open", "high", "low", "close", "volume"])


def _prices_to_dataframe(symbols: list[str], prices: dict[str, float]) -> pd.DataFrame:
    """Build a one-row-per-symbol DataFrame with close from prices dict."""
    rows = [{"symbol": s, "open": p, "high": p, "low": p, "close": p, "volume": 0} for s, p in prices.items() if s in symbols]
    return pd.DataFrame(rows) if rows else pd.DataFrame(columns=["symbol", "close"])


class PaperBrokerAdapter(BrokerAdapter):
    """
    Paper trading adapter. Simulates fills at latest price from get_market_data.
    Maintains internal cash and positions; get_portfolio returns that state.
    Market data: pass market_data_source(symbols -> DataFrame), or latest_prices (dict symbol -> price).
    """

    def __init__(
        self,
        initial_cash: float = 0.0,
        *,
        market_data_source: Callable[[list[str]], pd.DataFrame] | None = None,
        latest_prices: dict[str, float] | None = None,
    ) -> None:
        self._cash = initial_cash
        self._positions: dict[str, float] = {}
        self._order_log: list[tuple[Order, OrderStatus]] = []
        if market_data_source is not None:
            self._market_data_source = market_data_source
        elif latest_prices is not None:
            self._market_data_source = lambda syms: _prices_to_dataframe(syms, latest_prices)
        else:
            self._market_data_source = _default_market_data

    def submit_order(self, order: Order) -> OrderStatus:
        """Simulate fill at latest close price for order.symbol."""
        df = self.get_market_data([order.symbol])
        if df.empty or "close" not in df.columns:
            status = OrderStatus(
                status=OrderStatusKind.REJECTED,
                message="No market data for symbol",
                timestamp=datetime.now(),
            )
            self._order_log.append((order, status))
            return status

        if "symbol" in df.columns:
            sub = df[df["symbol"] == order.symbol]
            row = sub.iloc[0] if len(sub) > 0 else df.iloc[0]
        else:
            row = df.iloc[0]
        price = float(row.get("close", row.get("last", 0)))
        if price <= 0:
            status = OrderStatus(
                status=OrderStatusKind.REJECTED,
                message="Invalid price",
                timestamp=datetime.now(),
            )
            self._order_log.append((order, status))
            return status

        cost = order.quantity * price
        if order.side == Side.BUY:
            if self._cash < cost:
                status = OrderStatus(
                    status=OrderStatusKind.REJECTED,
                    message="Insufficient cash",
                    timestamp=datetime.now(),
                )
                self._order_log.append((order, status))
                return status
            self._cash -= cost
            self._positions[order.symbol] = self._positions.get(order.symbol, 0) + order.quantity
        else:
            pos = self._positions.get(order.symbol, 0)
            if pos < order.quantity:
                status = OrderStatus(
                    status=OrderStatusKind.REJECTED,
                    message="Insufficient position",
                    timestamp=datetime.now(),
                )
                self._order_log.append((order, status))
                return status
            self._cash += order.quantity * price
            self._positions[order.symbol] = pos - order.quantity
            if self._positions[order.symbol] == 0:
                del self._positions[order.symbol]

        order_id = f"paper-{uuid.uuid4().hex[:12]}"
        status = OrderStatus(
            status=OrderStatusKind.FILLED,
            order_id=order_id,
            fill_price=price,
            filled_quantity=order.quantity,
            timestamp=datetime.now(),
        )
        self._order_log.append((order, status))
        return status

    def get_portfolio(self) -> PortfolioState:
        """Return current simulated portfolio state."""
        return PortfolioState(cash=self._cash, positions=dict(self._positions))

    def get_market_data(self, symbols: list[str]) -> pd.DataFrame:
        """Return market data from the injected source."""
        return self._market_data_source(symbols)

    def get_order_log(self) -> list[tuple[Order, OrderStatus]]:
        """Return log of all submitted orders and their status (for debugging/reporting)."""
        return list(self._order_log)
