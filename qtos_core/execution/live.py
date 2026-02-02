"""
Live broker adapter: plug into ExecutionEngine via BrokerAdapter.

Sandbox-first: sandbox=True by default. Real live orders are blocked unless
QTOS_LIVE_TRADING_ENABLED=true. All orders go through submit_order(); portfolio
and market data are fetched from the broker API.

TODO: Replace placeholder auth and API calls with real broker SDK (e.g. Alpaca, IBKR, Binance).
"""

from __future__ import annotations

import logging
import os
import uuid
from datetime import datetime
from typing import Callable

import pandas as pd

from qtos_core.order import Order
from qtos_core.signal import Side

from qtos_core.execution.broker import BrokerAdapter
from qtos_core.execution.types import OrderStatus, OrderStatusKind, PortfolioState

logger = logging.getLogger(__name__)

# Environment variable that must be set to "true" to allow live (non-sandbox) order submission.
LIVE_TRADING_ENV = "QTOS_LIVE_TRADING_ENABLED"


def _resolve_symbol(internal: str, symbol_map: dict[str, str] | None) -> str:
    """Map internal symbol to broker symbol. Identity if no map or not present."""
    if symbol_map and internal in symbol_map:
        return symbol_map[internal]
    return internal


class LiveBrokerAdapter(BrokerAdapter):
    """
    Live broker adapter. Routes orders to broker API; fetches portfolio and market data.

    - sandbox=True (default): use broker paper/sandbox endpoint; no real money.
    - sandbox=False: real live trading; requires QTOS_LIVE_TRADING_ENABLED=true or
      orders are rejected.

    Symbol mapping: internal symbol → broker symbol via symbol_map (e.g. "SPY" → "SPY" or "BTC" → "BTCUSD").
    """

    def __init__(
        self,
        api_key: str,
        api_secret: str,
        sandbox: bool = True,
        base_url: str | None = None,
        symbol_map: dict[str, str] | None = None,
        *,
        initial_cash: float = 0.0,
        market_data_source: Callable[[list[str]], pd.DataFrame] | None = None,
    ) -> None:
        self._api_key = api_key
        self._api_secret = api_secret
        self._sandbox = sandbox
        self._base_url = base_url
        self._symbol_map = symbol_map or {}
        self._market_data_source = market_data_source
        self._session_authenticated = False
        # Sandbox-only: simulated cash/positions when no real broker state (e.g. placeholder API).
        self._sandbox_cash = initial_cash
        self._sandbox_positions: dict[str, float] = {}

        # TODO: Replace with real broker SDK authentication when integrating a specific broker.
        # Example: self._client = alpaca_trade_api.REST(api_key, api_secret, base_url=paper_url)
        self._authenticate()

        if self._sandbox:
            logger.info(
                "LiveBrokerAdapter: SANDBOX / PAPER mode is ACTIVE. Orders will go to broker paper endpoint."
            )
        else:
            if os.environ.get(LIVE_TRADING_ENV, "").lower() != "true":
                logger.warning(
                    "LiveBrokerAdapter: live trading is disabled. Set %s=true to allow real orders.",
                    LIVE_TRADING_ENV,
                )
            else:
                logger.warning(
                    "LiveBrokerAdapter: LIVE TRADING is ENABLED. Real money at risk."
                )

    def _authenticate(self) -> None:
        """Authenticate with the broker API. Placeholder until SDK is integrated."""
        # TODO: Call broker auth (e.g. REST login, OAuth). For now we only flag readiness.
        self._session_authenticated = True
        logger.debug("LiveBrokerAdapter: authentication placeholder completed.")

    def submit_order(self, order: Order) -> OrderStatus:
        """
        Submit an order to the broker. Market orders only in this implementation.

        Behavior:
        - If sandbox=False and QTOS_LIVE_TRADING_ENABLED != "true", returns REJECTED.
        - Translates internal Order to broker format, submits, maps response to OrderStatus.
        - Handles: accepted (PENDING), rejected, partially filled, filled.
        - On API errors: returns REJECTED OrderStatus with reason; no silent failures.
        """
        mode = "sandbox" if self._sandbox else "live"
        broker_symbol = _resolve_symbol(order.symbol, self._symbol_map)
        logger.info(
            "Submitting order: symbol=%s (broker=%s), side=%s, qty=%s, mode=%s",
            order.symbol,
            broker_symbol,
            order.side.value,
            order.quantity,
            mode,
        )

        if not self._sandbox and os.environ.get(LIVE_TRADING_ENV, "").lower() != "true":
            reason = (
                f"Live trading disabled. Set {LIVE_TRADING_ENV}=true to allow real orders."
            )
            logger.warning("Order rejected: %s", reason)
            return OrderStatus(
                status=OrderStatusKind.REJECTED,
                message=reason,
                timestamp=datetime.now(),
            )

        try:
            # TODO: Replace with real broker order submission.
            # 1. Build broker-specific order payload (e.g. symbol=broker_symbol, qty, side, type=market).
            # 2. POST to sandbox or live endpoint based on self._sandbox.
            # 3. Map broker response to OrderStatus (accepted -> PENDING, filled -> FILLED, etc.).
            # For now we simulate an immediate fill in sandbox to satisfy the interface.
            return self._submit_order_impl(order, broker_symbol, mode)
        except Exception as e:  # noqa: BLE001
            reason = f"Broker API error: {e!s}"
            logger.exception("Order submission failed: %s", reason)
            return OrderStatus(
                status=OrderStatusKind.REJECTED,
                message=reason,
                timestamp=datetime.now(),
            )

    def _submit_order_impl(
        self, order: Order, broker_symbol: str, mode: str
    ) -> OrderStatus:
        """
        Placeholder implementation: in sandbox, simulate immediate fill; otherwise reject.

        TODO: Replace with actual broker API call and response mapping.
        """
        if self._sandbox:
            # Sandbox: simulate immediate fill. In real integration, call broker paper API
            # and map their response (e.g. order_id, filled_qty, filled_price) to OrderStatus.
            order_id = f"live-sandbox-{uuid.uuid4().hex[:12]}"
            fill_price = 0.0
            df = self.get_market_data([order.symbol])
            if not df.empty and "close" in df.columns:
                if "symbol" in df.columns:
                    sub = df[df["symbol"] == order.symbol]
                    row = sub.iloc[-1] if len(sub) > 0 else df.iloc[-1]
                else:
                    row = df.iloc[-1]
                fill_price = float(row.get("close", 0.0))
            if order.side == Side.SELL:
                pos = self._sandbox_positions.get(order.symbol, 0)
                if pos < order.quantity:
                    logger.warning("Order rejected (sandbox): insufficient position %s for %s", pos, order.symbol)
                    return OrderStatus(
                        status=OrderStatusKind.REJECTED,
                        message="Insufficient position (sandbox)",
                        timestamp=datetime.now(),
                    )
            else:
                cost = order.quantity * (fill_price if fill_price > 0 else 0)
                if cost > 0 and self._sandbox_cash < cost:
                    logger.warning("Order rejected (sandbox): insufficient cash %.2f for cost %.2f", self._sandbox_cash, cost)
                    return OrderStatus(
                        status=OrderStatusKind.REJECTED,
                        message="Insufficient cash (sandbox)",
                        timestamp=datetime.now(),
                    )
            logger.info(
                "Broker response (sandbox simulated): order_id=%s, status=filled, fill_price=%s",
                order_id,
                fill_price,
            )
            # Update sandbox portfolio state so get_portfolio() reflects the fill.
            if order.side == Side.BUY:
                self._sandbox_cash -= order.quantity * fill_price if fill_price > 0 else 0.0
                self._sandbox_positions[order.symbol] = (
                    self._sandbox_positions.get(order.symbol, 0) + order.quantity
                )
            else:
                self._sandbox_positions[order.symbol] = (
                    self._sandbox_positions.get(order.symbol, 0) - order.quantity
                )
                self._sandbox_cash += order.quantity * fill_price if fill_price > 0 else 0.0
                if self._sandbox_positions[order.symbol] <= 0:
                    self._sandbox_positions.pop(order.symbol, None)
            return OrderStatus(
                status=OrderStatusKind.FILLED,
                order_id=order_id,
                fill_price=fill_price,
                filled_quantity=order.quantity,
                timestamp=datetime.now(),
            )
        # Live: TODO call real broker API and map response.
        return OrderStatus(
            status=OrderStatusKind.REJECTED,
            message="Live broker API not implemented; use sandbox=True or add SDK integration.",
            timestamp=datetime.now(),
        )

    def get_portfolio(self) -> PortfolioState:
        """
        Return current portfolio snapshot from the broker: cash balance and open positions.

        TODO: Replace with real broker API (e.g. GET /account, GET /positions).
        Returns cash and positions (symbol -> quantity). Average entry prices are
        broker-specific; this type uses positions by quantity only.
        """
        try:
            # TODO: Call broker API for account/positions. Map to PortfolioState(cash=..., positions={}).
            # Example: account = self._client.get_account(); positions = self._client.list_positions()
            if self._sandbox:
                # Use simulated state when no real broker API; real sandbox would query broker paper API.
                return PortfolioState(cash=self._sandbox_cash, positions=dict(self._sandbox_positions))
            return PortfolioState(cash=0.0, positions={})
        except Exception as e:  # noqa: BLE001
            logger.exception("get_portfolio failed: %s", e)
            return PortfolioState(cash=0.0, positions={})

    def get_market_data(self, symbols: list[str]) -> pd.DataFrame:
        """
        Fetch latest prices for the requested symbols from the broker.

        Returns a DataFrame with timestamp index and columns suitable for pricing
        (e.g. symbol, open, high, low, close, volume). If the broker does not
        support bulk price fetch, requests may be per-symbol (documented limitation).

        TODO: Replace with real broker market data API (e.g. bars, quotes, last trade).
        """
        if not symbols:
            return pd.DataFrame(columns=["symbol", "open", "high", "low", "close", "volume"])

        if self._sandbox and self._market_data_source is not None:
            return self._market_data_source(symbols)

        try:
            # TODO: Call broker API for latest bars/quotes per symbol. Map to DataFrame.
            # Limitation: some brokers only support single-symbol or limited bulk; loop if needed.
            broker_symbols = [_resolve_symbol(s, self._symbol_map) for s in symbols]
            logger.debug("get_market_data requested: %s (broker: %s)", symbols, broker_symbols)
            # Placeholder: empty DataFrame. Real implementation would fill rows indexed by timestamp.
            return pd.DataFrame(columns=["symbol", "open", "high", "low", "close", "volume"])
        except Exception as e:  # noqa: BLE001
            logger.exception("get_market_data failed: %s", e)
            return pd.DataFrame(columns=["symbol", "open", "high", "low", "close", "volume"])
