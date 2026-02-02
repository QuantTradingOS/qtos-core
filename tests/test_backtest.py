"""
Tests for backtesting: BacktestEngine, PassThroughRiskManager, metrics.
"""

from datetime import datetime

import pandas as pd
import pytest

from backtesting import BacktestEngine, compute_metrics
from backtesting.engine import PassThroughRiskManager
from qtos_core import Order, Portfolio, Signal
from qtos_core.order import OrderType
from qtos_core.signal import Side
from qtos_core.examples.buy_and_hold import BuyAndHoldStrategy


def _make_ohlcv_df(n_days: int = 5, symbol: str = "SPY") -> pd.DataFrame:
    """Minimal OHLCV DataFrame with DatetimeIndex."""
    dates = pd.date_range("2024-01-02", periods=n_days, freq="B")
    df = pd.DataFrame(
        {
            "open": [100.0 + i for i in range(n_days)],
            "high": [101.0 + i for i in range(n_days)],
            "low": [99.0 + i for i in range(n_days)],
            "close": [100.5 + i for i in range(n_days)],
            "volume": [1_000_000] * n_days,
        },
        index=dates,
    )
    df.index.name = "datetime"
    df.attrs["symbol"] = symbol
    return df


# --- PassThroughRiskManager ---


def test_pass_through_risk_approves_signal():
    risk = PassThroughRiskManager()
    portfolio = Portfolio(cash=100_000.0)
    sig = Signal(symbol="SPY", side=Side.BUY, quantity=10.0, timestamp=datetime.now())
    order = risk.check(sig, portfolio)
    assert order is not None
    assert order.symbol == "SPY"
    assert order.quantity == 10.0
    assert order.side == Side.BUY


def test_pass_through_risk_returns_order_unchanged():
    risk = PassThroughRiskManager()
    portfolio = Portfolio(cash=100_000.0)
    o = Order(symbol="QQQ", side=Side.SELL, quantity=5.0, order_type=OrderType.MARKET)
    out = risk.check(o, portfolio)
    assert out is o


# --- BacktestEngine ---


def test_backtest_engine_run_returns_result():
    data = _make_ohlcv_df(n_days=10)
    portfolio = Portfolio(cash=100_000.0)
    strategy = BuyAndHoldStrategy(symbol="SPY", quantity=50)
    risk = PassThroughRiskManager()
    engine = BacktestEngine(strategy, risk, portfolio)
    result = engine.run(data, symbol="SPY")
    assert result.portfolio is not None
    assert result.trades is not None
    assert result.equity_curve is not None
    assert len(result.equity_curve) == 10


def test_backtest_engine_buy_and_hold_one_fill():
    data = _make_ohlcv_df(n_days=5)
    portfolio = Portfolio(cash=100_000.0)
    strategy = BuyAndHoldStrategy(symbol="SPY", quantity=50)
    risk = PassThroughRiskManager()
    engine = BacktestEngine(strategy, risk, portfolio)
    result = engine.run(data, symbol="SPY")
    assert len(result.trades) == 1
    assert result.trades[0].symbol == "SPY"
    assert result.trades[0].quantity == 50
    assert result.trades[0].price == 100.5  # close of first bar (strategy fires on first event)
    assert result.portfolio.position("SPY") == 50
    assert result.portfolio.cash == 100_000.0 - 50 * 100.5  # filled at first bar close


def test_backtest_engine_equity_curve_length():
    data = _make_ohlcv_df(n_days=3)
    portfolio = Portfolio(cash=1000.0)
    strategy = BuyAndHoldStrategy(symbol="SPY", quantity=1)
    engine = BacktestEngine(strategy, PassThroughRiskManager(), portfolio)
    result = engine.run(data, symbol="SPY")
    assert len(result.equity_curve) == 3


# --- compute_metrics ---


def test_compute_metrics_basic():
    from datetime import datetime
    curve = [
        (datetime(2024, 1, 1), 100_000.0),
        (datetime(2024, 1, 2), 100_500.0),
        (datetime(2024, 12, 31), 110_000.0),
    ]
    m = compute_metrics(100_000.0, curve)
    assert m.initial_value == 100_000.0
    assert m.final_value == 110_000.0
    assert m.total_pnl == 10_000.0
    assert m.total_return_pct == 10.0


def test_compute_metrics_empty_curve():
    m = compute_metrics(100_000.0, [])
    assert m.final_value == 100_000.0
    assert m.total_pnl == 0.0
    assert m.sharpe_ratio == 0.0
