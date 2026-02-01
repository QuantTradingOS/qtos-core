"""
Backtesting engine: orchestrates market events through EventLoop.

Loads data → builds MarketEvents → runs Strategy → RiskManager → Portfolio updates.
Agent hooks: Advisors (modify signals), Validators (modify orders), Observers (post-trade).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any, Protocol

import pandas as pd

from qtos_core import Event, EventLoop, Order, Portfolio, RiskManager, Signal, Strategy
from qtos_core.order import OrderType
from qtos_core.signal import Side

if TYPE_CHECKING:
    from collections.abc import Sequence


@dataclass(frozen=True)
class MarketData:
    """Payload for a market event: one bar per symbol."""

    symbol: str
    open: float
    high: float
    low: float
    close: float
    volume: float = 0.0


@dataclass
class Trade:
    """Record of a filled order in the backtest."""

    symbol: str
    side: Side
    quantity: float
    price: float
    timestamp: datetime


# --- Agent integration: protocols (advisors, validators, observers) ---


class Advisor(Protocol):
    """Agent hook: modify signals before risk check. E.g. MarketRegime, Sentiment."""

    def __call__(
        self,
        signals: list[Signal],
        event: Event,
        portfolio: Portfolio,
    ) -> list[Signal]:
        """Return modified (or filtered) signals."""
        ...


class Validator(Protocol):
    """Agent hook: modify or reject order after risk check. E.g. CapitalGuardian."""

    def __call__(self, order: Order, portfolio: Portfolio) -> Order | None:
        """Return order to allow, or None to reject."""
        ...


class Observer(Protocol):
    """Agent hook: post-trade analysis."""

    def __call__(self, trade: Trade, portfolio: Portfolio) -> None:
        """Called after each fill (e.g. log, metrics)."""
        ...


# --- Pass-through risk (for demos) ---


class PassThroughRiskManager(RiskManager):
    """Approves all signals as market orders. No size/risk limits."""

    def check(
        self,
        signal_or_order: Signal | Order,
        portfolio: Portfolio,
    ) -> Order | None:
        if isinstance(signal_or_order, Order):
            return signal_or_order
        s = signal_or_order
        return Order(
            symbol=s.symbol,
            side=s.side,
            quantity=s.quantity,
            order_type=OrderType.MARKET,
            limit_price=None,
            timestamp=s.timestamp,
        )


# --- Engine ---


@dataclass
class BacktestResult:
    """Result of a backtest run: portfolio, trades, equity curve."""

    portfolio: Portfolio
    trades: list[Trade] = field(default_factory=list)
    equity_curve: list[tuple[datetime, float]] = field(default_factory=list)


class BacktestEngine:
    """
    Orchestrates a backtest: build events from OHLCV data, run EventLoop,
    strategy → advisors → risk → validators → fill → observers; record trades and equity.
    """

    def __init__(
        self,
        strategy: Strategy,
        risk_manager: RiskManager,
        portfolio: Portfolio,
        *,
        advisors: Sequence[Advisor] = (),
        validators: Sequence[Validator] = (),
        observers: Sequence[Observer] = (),
    ) -> None:
        self.strategy = strategy
        self.risk_manager = risk_manager
        self.portfolio = portfolio
        self.advisors: list[Advisor] = list(advisors)
        self.validators: list[Validator] = list(validators)
        self.observers: list[Observer] = list(observers)
        self._trades: list[Trade] = []
        self._equity_curve: list[tuple[datetime, float]] = []
        self._last_prices: dict[str, float] = {}

    def _events_from_dataframe(
        self,
        df: pd.DataFrame,
        symbol: str,
    ) -> list[Event]:
        """Build a list of Event with MarketData payload from OHLCV DataFrame."""
        events: list[Event] = []
        for ts, row in df.iterrows():
            ts_dt = ts.to_pydatetime() if hasattr(ts, "to_pydatetime") else datetime.fromisoformat(str(ts))
            payload = MarketData(
                symbol=symbol,
                open=float(row.get("open", row.get("close", 0))),
                high=float(row.get("high", row.get("close", 0))),
                low=float(row.get("low", row.get("close", 0))),
                close=float(row["close"]),
                volume=float(row.get("volume", 0)),
            )
            events.append(Event(timestamp=ts_dt, payload=payload))
        return events

    def _portfolio_value(self) -> float:
        """Current portfolio value: cash + positions at last known prices."""
        total = self.portfolio.cash
        for sym, qty in self.portfolio.positions.items():
            total += qty * self._last_prices.get(sym, 0.0)
        return total

    def _handle_event(self, event: Event) -> None:
        """Process one event: strategy → advisors → risk → validators → fill → observers."""
        payload = event.payload
        if isinstance(payload, MarketData):
            self._last_prices[payload.symbol] = payload.close
        else:
            return

        # Strategy
        signals = self.strategy.on_event(event, self.portfolio)

        # Advisors (modify signals)
        for advisor in self.advisors:
            signals = advisor(signals, event, self.portfolio)

        # Risk + validators → fill
        for sig in signals:
            order = self.risk_manager.check(sig, self.portfolio)
            if order is None:
                continue
            for validator in self.validators:
                order = validator(order, self.portfolio)
                if order is None:
                    break
            if order is None:
                continue

            # Fill at current close (same bar)
            price = self._last_prices.get(order.symbol, 0.0)
            if price <= 0:
                continue
            cost = order.quantity * price
            if order.side == Side.BUY:
                if self.portfolio.cash < cost:
                    continue
                self.portfolio.cash -= cost
                self.portfolio.update_position(order.symbol, order.quantity)
            else:
                pos = self.portfolio.position(order.symbol)
                if pos < order.quantity:
                    order = Order(
                        symbol=order.symbol,
                        side=order.side,
                        quantity=pos,
                        order_type=order.order_type,
                        limit_price=order.limit_price,
                        timestamp=order.timestamp,
                    )
                    if order.quantity <= 0:
                        continue
                self.portfolio.cash += order.quantity * price
                self.portfolio.update_position(order.symbol, -order.quantity)

            trade = Trade(
                symbol=order.symbol,
                side=order.side,
                quantity=order.quantity,
                price=price,
                timestamp=order.timestamp or event.timestamp,
            )
            self._trades.append(trade)
            for obs in self.observers:
                obs(trade, self.portfolio)

        # Equity snapshot
        self._equity_curve.append((event.timestamp, self._portfolio_value()))

    def run(
        self,
        data: pd.DataFrame,
        symbol: str | None = None,
    ) -> BacktestResult:
        """
        Run backtest over the given OHLCV DataFrame.

        Parameters
        ----------
        data : pd.DataFrame
            DataFrame with DatetimeIndex and open, high, low, close [, volume].
        symbol : str, optional
            Symbol for market payloads. If None, uses data.attrs.get('symbol', 'UNKNOWN').

        Returns
        -------
        BacktestResult
            Portfolio, trades, and equity curve.
        """
        self._trades = []
        self._equity_curve = []
        self._last_prices = {}
        sym = symbol or (data.attrs.get("symbol", "UNKNOWN") if hasattr(data, "attrs") else "UNKNOWN")

        events = self._events_from_dataframe(data, sym)
        loop = EventLoop()
        loop.subscribe(self._handle_event)
        loop.run(events)

        return BacktestResult(
            portfolio=Portfolio(cash=self.portfolio.cash, positions=dict(self.portfolio.positions)),
            trades=list(self._trades),
            equity_curve=list(self._equity_curve),
        )
