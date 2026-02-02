"""
Tests for execution layer: PaperBrokerAdapter, ExecutionEngine, types.
"""

from datetime import datetime

from qtos_core import Order, Portfolio
from qtos_core.order import OrderType
from qtos_core.signal import Side
from qtos_core.execution import ExecutionEngine, PaperBrokerAdapter
from qtos_core.execution.types import OrderStatusKind, PortfolioState
from qtos_core.examples.buy_and_hold import BuyAndHoldStrategy
from backtesting.engine import PassThroughRiskManager


def test_paper_broker_get_portfolio_initial():
    broker = PaperBrokerAdapter(initial_cash=50_000.0)
    state = broker.get_portfolio()
    assert state.cash == 50_000.0
    assert state.positions == {}
    assert state.position("SPY") == 0.0


def test_paper_broker_submit_buy_fill():
    broker = PaperBrokerAdapter(initial_cash=100_000.0, latest_prices={"SPY": 400.0})
    order = Order(symbol="SPY", side=Side.BUY, quantity=10.0, order_type=OrderType.MARKET)
    status = broker.submit_order(order)
    assert status.status == OrderStatusKind.FILLED
    assert status.fill_price == 400.0
    assert status.filled_quantity == 10.0
    state = broker.get_portfolio()
    assert state.cash == 100_000.0 - 10.0 * 400.0
    assert state.position("SPY") == 10.0


def test_paper_broker_submit_sell_fill():
    broker = PaperBrokerAdapter(initial_cash=20.0 * 405.0, latest_prices={"SPY": 405.0})
    broker.submit_order(Order(symbol="SPY", side=Side.BUY, quantity=20.0, order_type=OrderType.MARKET))
    order = Order(symbol="SPY", side=Side.SELL, quantity=10.0, order_type=OrderType.MARKET)
    status = broker.submit_order(order)
    assert status.status == OrderStatusKind.FILLED
    state = broker.get_portfolio()
    assert state.position("SPY") == 10.0


def test_paper_broker_rejects_no_market_data():
    broker = PaperBrokerAdapter(initial_cash=100_000.0)  # no latest_prices
    order = Order(symbol="SPY", side=Side.BUY, quantity=10.0, order_type=OrderType.MARKET)
    status = broker.submit_order(order)
    assert status.status == OrderStatusKind.REJECTED


def test_paper_broker_rejects_insufficient_cash():
    broker = PaperBrokerAdapter(initial_cash=100.0, latest_prices={"SPY": 400.0})
    order = Order(symbol="SPY", side=Side.BUY, quantity=100.0, order_type=OrderType.MARKET)
    status = broker.submit_order(order)
    assert status.status == OrderStatusKind.REJECTED


def test_execution_engine_run_once():
    broker = PaperBrokerAdapter(initial_cash=100_000.0, latest_prices={"SPY": 400.0})
    strategy = BuyAndHoldStrategy(symbol="SPY", quantity=10)
    engine = ExecutionEngine(strategy, PassThroughRiskManager(), broker)
    engine.run_once(["SPY"])
    state = broker.get_portfolio()
    assert state.position("SPY") == 10.0
    assert state.cash == 100_000.0 - 10.0 * 400.0


def test_execution_engine_kill_switch_blocks_orders():
    broker = PaperBrokerAdapter(initial_cash=100_000.0, latest_prices={"SPY": 400.0})
    strategy = BuyAndHoldStrategy(symbol="SPY", quantity=10)
    engine = ExecutionEngine(strategy, PassThroughRiskManager(), broker)
    engine.set_kill_switch(True)
    engine.run_once(["SPY"])
    state = broker.get_portfolio()
    assert state.position("SPY") == 0.0
    assert state.cash == 100_000.0  # no order submitted; kill switch causes early return
