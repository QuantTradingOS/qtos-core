"""
Paper trading example: run a strategy in paper mode with execution layer.

Shows: PaperBrokerAdapter, ExecutionEngine, advisors/validators/observers hooks,
portfolio and order log in real-time. Same strategy interface as backtesting.
"""

from __future__ import annotations

from datetime import datetime
from qtos_core import Portfolio, Strategy, Signal
from qtos_core.examples.buy_and_hold import BuyAndHoldStrategy
from qtos_core.execution import (
    ExecutionEngine,
    PaperBrokerAdapter,
    ExecutedTrade,
    RejectedOrderLog,
)
from qtos_core.events import Event
from qtos_core.order import Order
from backtesting.engine import PassThroughRiskManager


# --- Example advisors, validators, observers (same signatures as backtesting) ---


def log_signals_advisor(signals: list[Signal], event: Event, portfolio: Portfolio) -> list[Signal]:
    """Advisor: log signals before risk (e.g. MarketRegime, Sentiment could modify here)."""
    if signals:
        print(f"  [Advisor] {len(signals)} signal(s) at {event.timestamp}")
    return signals


def max_size_validator(order: Order, portfolio: Portfolio) -> Order | None:
    """Validator: cap size at 100 (e.g. CapitalGuardian could enforce exposure here)."""
    if order.quantity > 100:
        from qtos_core.order import OrderType
        return Order(
            symbol=order.symbol,
            side=order.side,
            quantity=100,
            order_type=order.order_type,
            limit_price=order.limit_price,
            timestamp=order.timestamp,
        )
    return order


def print_fill_observer(trade: ExecutedTrade, portfolio: Portfolio) -> None:
    """Observer: post-trade log (e.g. journal, metrics)."""
    print(f"  [Observer] FILL {trade.side.value} {trade.quantity} {trade.symbol} @ {trade.price:.2f}")


def main() -> None:
    symbol = "SPY"
    initial_cash = 100_000.0
    # Simulated latest prices (in real use, feed from market data)
    latest_prices: dict[str, float] = {symbol: 400.0}

    # Paper broker with price source
    broker = PaperBrokerAdapter(initial_cash=initial_cash, latest_prices=latest_prices)
    strategy = BuyAndHoldStrategy(symbol=symbol, quantity=50)
    risk_manager = PassThroughRiskManager()

    engine = ExecutionEngine(
        strategy=strategy,
        risk_manager=risk_manager,
        broker=broker,
        advisors=[log_signals_advisor],
        validators=[max_size_validator],
        observers=[print_fill_observer],
        daily_pnl_limit=5000.0,
        max_position_per_trade=200.0,
    )

    print("--- Paper trading: run_once (first bar) ---")
    engine.run_once([symbol], event_timestamp=datetime.now())
    state = broker.get_portfolio()
    print(f"Portfolio: cash={state.cash:.2f}, positions={state.positions}")
    for order, status in broker.get_order_log():
        print(f"  Order log: {order.symbol} {order.side.value} {order.quantity} -> {status.status.value}")

    print("\n--- Paper trading: run_once (second bar, no new signal from buy-and-hold) ---")
    latest_prices[symbol] = 402.0
    engine.run_once([symbol], event_timestamp=datetime.now())
    state = broker.get_portfolio()
    print(f"Portfolio: cash={state.cash:.2f}, positions={state.positions}")

    print("\n--- Rejected log (if any) ---")
    for entry in engine.get_rejected_log():
        print(f"  Rejected: reason={entry.reason}, order={entry.order}, signal={entry.signal}")


if __name__ == "__main__":
    main()
