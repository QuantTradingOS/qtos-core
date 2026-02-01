"""
Execution engine: run strategy through broker adapter with advisors, validators, observers.

Enforces safety (daily PnL limit, max position per trade, kill switch); logs rejected orders.
Same flow as backtesting: strategy → advisors → risk → validators → submit → observers on fill.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Protocol

from qtos_core import Event, Order, Portfolio, RiskManager, Signal, Strategy
from qtos_core.execution.broker import BrokerAdapter
from qtos_core.execution.types import ExecutedTrade, OrderStatusKind, PortfolioState

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


# --- Agent hooks (compatible with backtesting.engine.Advisor / Validator / Observer) ---


class ExecutionAdvisor(Protocol):
    """Modify signals before risk. Same signature as backtesting Advisor."""

    def __call__(self, signals: list[Signal], event: Event, portfolio: Portfolio) -> list[Signal]:
        ...


class ExecutionValidator(Protocol):
    """Modify or reject order after risk. Same signature as backtesting Validator."""

    def __call__(self, order: Order, portfolio: Portfolio) -> Order | None:
        ...


class ExecutionObserver(Protocol):
    """Post-trade callback. Same signature as backtesting Observer (trade has symbol, side, quantity, price, timestamp)."""

    def __call__(self, trade: ExecutedTrade, portfolio: Portfolio) -> None:
        ...


@dataclass
class RejectedOrderLog:
    """One entry for a rejected or blocked order (order set when past risk; else signal)."""

    reason: str
    timestamp: datetime
    order: Order | None = None
    signal: Signal | None = None


class ExecutionEngine:
    """
    Run strategy in paper or live mode via BrokerAdapter.
    Flow: get market data → build event → strategy → advisors → risk → validators
    → safety checks → submit_order → on fill: observers.
    Safety: daily PnL limit, max position per trade, kill switch. Rejected orders are logged.
    """

    def __init__(
        self,
        strategy: Strategy,
        risk_manager: RiskManager,
        broker: BrokerAdapter,
        *,
        advisors: Sequence[ExecutionAdvisor] = (),
        validators: Sequence[ExecutionValidator] = (),
        observers: Sequence[ExecutionObserver] = (),
        daily_pnl_limit: float | None = None,
        max_position_per_trade: float | None = None,
        kill_switch: bool = False,
    ) -> None:
        self.strategy = strategy
        self.risk_manager = risk_manager
        self.broker = broker
        self.advisors: list[ExecutionAdvisor] = list(advisors)
        self.validators: list[ExecutionValidator] = list(validators)
        self.observers: list[ExecutionObserver] = list(observers)
        self.daily_pnl_limit = daily_pnl_limit
        self.max_position_per_trade = max_position_per_trade
        self._kill_switch = kill_switch
        self._rejected_log: list[RejectedOrderLog] = []
        self._daily_start_equity: float | None = None

    def set_kill_switch(self, value: bool) -> None:
        """Emergency stop: when True, all orders are blocked."""
        self._kill_switch = value

    def get_rejected_log(self) -> list[RejectedOrderLog]:
        """Return log of rejected/blocked orders for debugging and reporting."""
        return list(self._rejected_log)

    def _portfolio_from_state(self, state: PortfolioState) -> Portfolio:
        """Build a Portfolio view for strategy and hooks (read-only usage)."""
        return Portfolio(cash=state.cash, positions=dict(state.positions))

    def _current_equity(self, state: PortfolioState, prices: dict[str, float]) -> float:
        """Portfolio value at current prices."""
        total = state.cash
        for sym, qty in state.positions.items():
            total += qty * prices.get(sym, 0.0)
        return total

    def _prices_from_market_data(self, symbols: list[str]) -> dict[str, float]:
        """Get latest close price per symbol from broker."""
        df = self.broker.get_market_data(symbols)
        prices: dict[str, float] = {}
        if df.empty:
            return prices
        if "symbol" in df.columns:
            for sym in symbols:
                sub = df[df["symbol"] == sym]
                if not sub.empty:
                    row = sub.iloc[-1]
                    prices[sym] = float(row.get("close", row.get("last", 0)))
        else:
            for sym in symbols:
                if sym in df.columns:
                    prices[sym] = float(df[sym].iloc[-1])
                elif not df.empty:
                    prices[sym] = float(df["close"].iloc[-1]) if "close" in df.columns else 0.0
        return prices

    def run_once(
        self,
        symbols: list[str],
        *,
        event_timestamp: datetime | None = None,
    ) -> None:
        """
        Run one execution cycle: fetch market data, run strategy, advisors, risk, validators,
        apply safety checks, submit orders, run observers on fills.
        Call this from a scheduler or loop for paper/live; same API as backtesting step.
        """
        ts = event_timestamp or datetime.now()
        state = self.broker.get_portfolio()
        prices = self._prices_from_market_data(symbols)
        portfolio = self._portfolio_from_state(state)
        equity = self._current_equity(state, prices)

        # Daily PnL: reset daily start equity at first run or new day (simplified: no date tracking here; user can set)
        if self._daily_start_equity is None:
            self._daily_start_equity = equity

        if self._kill_switch:
            logger.warning("Execution blocked: kill switch is on")
            return

        # Build event payload (dict of symbol -> close for strategy compatibility)
        payload = {sym: prices.get(sym, 0.0) for sym in symbols}
        event = Event(timestamp=ts, payload=payload)

        # Strategy
        signals = self.strategy.on_event(event, portfolio)

        # Advisors
        for advisor in self.advisors:
            signals = advisor(signals, event, portfolio)

        # Risk + validators + safety → submit
        for sig in signals:
            order = self.risk_manager.check(sig, portfolio)
            if order is None:
                self._rejected_log.append(RejectedOrderLog(reason="risk_rejected", timestamp=ts, signal=sig))
                continue
            for validator in self.validators:
                rejected_order = order
                order = validator(order, portfolio)
                if order is None:
                    self._rejected_log.append(RejectedOrderLog(reason="validator_rejected", timestamp=ts, order=rejected_order))
                    break
            if order is None:
                continue

            if self._kill_switch:
                self._rejected_log.append(RejectedOrderLog(reason="kill_switch", timestamp=ts, order=order))
                continue
            if self.max_position_per_trade is not None and order.quantity > self.max_position_per_trade:
                self._rejected_log.append(RejectedOrderLog(reason="max_position_per_trade", timestamp=ts, order=order))
                logger.info("Order blocked: quantity %s > max_position_per_trade %s", order.quantity, self.max_position_per_trade)
                continue
            if self.daily_pnl_limit is not None:
                if equity - self._daily_start_equity <= -self.daily_pnl_limit:
                    self._rejected_log.append(RejectedOrderLog(reason="daily_pnl_limit", timestamp=ts, order=order))
                    logger.warning("Order blocked: daily PnL limit reached")
                    continue

            status = self.broker.submit_order(order)
            if status.status == OrderStatusKind.REJECTED:
                self._rejected_log.append(RejectedOrderLog(reason=status.message or "broker_rejected", timestamp=ts, order=order))
                logger.info("Order rejected: %s", status.message)
                continue
            if status.status == OrderStatusKind.FILLED and status.fill_price is not None:
                trade = ExecutedTrade(
                    symbol=order.symbol,
                    side=order.side,
                    quantity=status.filled_quantity if status.filled_quantity else order.quantity,
                    price=status.fill_price,
                    timestamp=status.timestamp or ts,
                    order_id=status.order_id,
                )
                # Refresh portfolio view for observers
                state_after = self.broker.get_portfolio()
                portfolio_after = self._portfolio_from_state(state_after)
                for obs in self.observers:
                    obs(trade, portfolio_after)

    def reset_daily_pnl_baseline(self) -> None:
        """Reset daily start equity to current equity (e.g. at start of day)."""
        state = self.broker.get_portfolio()
        prices = self._prices_from_market_data(list(state.positions.keys()) or ["UNKNOWN"])
        self._daily_start_equity = self._current_equity(state, prices)
