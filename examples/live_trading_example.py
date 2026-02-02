"""
Live trading example: run a strategy with LiveBrokerAdapter in sandbox mode.

Demonstrates:
- LiveBrokerAdapter with sandbox=True (default); no real orders.
- Same ExecutionEngine flow as paper: strategy → advisors → risk → validators → submit.
- Switching from PaperBrokerAdapter to LiveBrokerAdapter by swapping the broker only.
- Portfolio snapshot and order flow; no changes to strategy, agents, or engine.
"""

from __future__ import annotations

from datetime import datetime

import pandas as pd

from qtos_core import Portfolio
from qtos_core.examples.buy_and_hold import BuyAndHoldStrategy
from qtos_core.execution import (
    ExecutionEngine,
    ExecutedTrade,
    LiveBrokerAdapter,
    PaperBrokerAdapter,
)
from backtesting.engine import PassThroughRiskManager


def _prices_to_dataframe(symbols: list[str], prices: dict[str, float]) -> pd.DataFrame:
    """Build a one-row-per-symbol DataFrame with close from prices dict."""
    rows = [
        {"symbol": s, "open": p, "high": p, "low": p, "close": p, "volume": 0}
        for s, p in prices.items()
        if s in symbols
    ]
    return pd.DataFrame(rows) if rows else pd.DataFrame(columns=["symbol", "close"])


def print_fill_observer(trade: ExecutedTrade, portfolio: Portfolio) -> None:
    """Observer: post-trade log."""
    print(f"  [Observer] FILL {trade.side.value} {trade.quantity} {trade.symbol} @ {trade.price:.2f}")


def main() -> None:
    symbol = "SPY"
    initial_cash = 100_000.0
    latest_prices: dict[str, float] = {symbol: 400.0}

    # --- 1) Run with PaperBrokerAdapter (same as paper_trading_example) ---
    print("=== PaperBrokerAdapter (paper mode) ===\n")
    paper_broker = PaperBrokerAdapter(
        initial_cash=initial_cash,
        latest_prices=latest_prices,
    )
    strategy = BuyAndHoldStrategy(symbol=symbol, quantity=50)
    risk_manager = PassThroughRiskManager()
    engine = ExecutionEngine(
        strategy=strategy,
        risk_manager=risk_manager,
        broker=paper_broker,
        observers=[print_fill_observer],
        daily_pnl_limit=5000.0,
        max_position_per_trade=200.0,
    )
    engine.run_once([symbol], event_timestamp=datetime.now())
    state = paper_broker.get_portfolio()
    print(f"Portfolio: cash={state.cash:.2f}, positions={state.positions}")
    for order, status in paper_broker.get_order_log():
        print(f"  Order: {order.symbol} {order.side.value} {order.quantity} -> {status.status.value}")

    # --- 2) Switch to LiveBrokerAdapter (sandbox=True) ---
    print("\n=== LiveBrokerAdapter (sandbox mode) ===\n")
    # Use a fresh strategy so buy-and-hold can fire again for demo; in practice you'd reuse one.
    strategy2 = BuyAndHoldStrategy(symbol=symbol, quantity=25)
    live_broker = LiveBrokerAdapter(
        api_key="placeholder_key",
        api_secret="placeholder_secret",
        sandbox=True,
        initial_cash=initial_cash,
        market_data_source=lambda syms: _prices_to_dataframe(syms, latest_prices),
    )
    engine2 = ExecutionEngine(
        strategy=strategy2,
        risk_manager=risk_manager,
        broker=live_broker,
        observers=[print_fill_observer],
        daily_pnl_limit=5000.0,
        max_position_per_trade=200.0,
    )
    engine2.run_once([symbol], event_timestamp=datetime.now())
    state2 = live_broker.get_portfolio()
    print(f"Portfolio: cash={state2.cash:.2f}, positions={state2.positions}")

    print("\n--- Rejected log (if any) ---")
    for entry in engine2.get_rejected_log():
        print(f"  Rejected: reason={entry.reason}, order={entry.order}, signal={entry.signal}")

    print("\n--- Done: same engine interface; only the broker adapter changed (Paper → Live sandbox). ---")


if __name__ == "__main__":
    main()
