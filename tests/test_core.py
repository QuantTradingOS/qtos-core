"""
Tests for qtos_core: Event, EventLoop, Signal, Order, Portfolio, Strategy.
"""

from datetime import datetime

import pytest

from qtos_core import Event, EventLoop, Order, Portfolio, Signal, Strategy
from qtos_core.order import OrderType
from qtos_core.signal import Side
from qtos_core.examples.buy_and_hold import BuyAndHoldStrategy


# --- Event ---


def test_event_creation():
    ts = datetime(2024, 1, 15, 10, 0, 0)
    e = Event(timestamp=ts, payload={"close": 100.0})
    assert e.timestamp == ts
    assert e.payload == {"close": 100.0}


def test_event_immutable():
    e = Event(timestamp=datetime.now(), payload=None)
    with pytest.raises(AttributeError):
        e.timestamp = datetime(2024, 1, 1)


# --- EventLoop ---


def test_event_loop_dispatch_order():
    log = []
    loop = EventLoop()
    loop.subscribe(lambda ev: log.append(("a", ev)))
    loop.subscribe(lambda ev: log.append(("b", ev)))
    ev = Event(timestamp=datetime.now(), payload=1)
    loop.dispatch(ev)
    assert log == [("a", ev), ("b", ev)]


def test_event_loop_run():
    log = []
    loop = EventLoop()
    loop.subscribe(lambda ev: log.append(ev.payload))
    events = [
        Event(timestamp=datetime.now(), payload=1),
        Event(timestamp=datetime.now(), payload=2),
    ]
    loop.run(events)
    assert log == [1, 2]


# --- Signal & Order ---


def test_signal_creation():
    ts = datetime.now()
    s = Signal(symbol="SPY", side=Side.BUY, quantity=10.0, timestamp=ts)
    assert s.symbol == "SPY"
    assert s.side == Side.BUY
    assert s.quantity == 10.0
    assert s.timestamp == ts


def test_order_creation():
    o = Order(symbol="SPY", side=Side.SELL, quantity=5.0, order_type=OrderType.MARKET)
    assert o.symbol == "SPY"
    assert o.side == Side.SELL
    assert o.quantity == 5.0
    assert o.order_type == OrderType.MARKET
    assert o.limit_price is None


# --- Portfolio ---


def test_portfolio_initial_state():
    p = Portfolio(cash=100_000.0)
    assert p.cash == 100_000.0
    assert p.positions == {}
    assert p.position("SPY") == 0.0


def test_portfolio_update_position_buy():
    p = Portfolio(cash=1000.0)
    p.update_position("SPY", 10.0)
    assert p.position("SPY") == 10.0
    assert p.positions == {"SPY": 10.0}


def test_portfolio_update_position_sell():
    p = Portfolio(cash=0.0, positions={"SPY": 10.0})
    p.update_position("SPY", -4.0)
    assert p.position("SPY") == 6.0
    p.update_position("SPY", -6.0)
    assert p.position("SPY") == 0.0
    assert "SPY" not in p.positions


# --- BuyAndHoldStrategy ---


def test_buy_and_hold_emits_once():
    strategy = BuyAndHoldStrategy(symbol="SPY", quantity=50)
    portfolio = Portfolio(cash=100_000.0)
    ev = Event(timestamp=datetime.now(), payload=None)
    signals1 = strategy.on_event(ev, portfolio)
    assert len(signals1) == 1
    assert signals1[0].symbol == "SPY"
    assert signals1[0].side == Side.BUY
    assert signals1[0].quantity == 50
    signals2 = strategy.on_event(ev, portfolio)
    assert len(signals2) == 0
