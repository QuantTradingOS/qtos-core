"""
qtos-core: Deterministic event-driven trading core engine.

No AI, Streamlit, or broker integrations. Strong interfaces, clear separation of concerns.
"""

__version__ = "0.1.0"

from qtos_core.events import Event
from qtos_core.event_loop import EventLoop
from qtos_core.signal import Signal
from qtos_core.order import Order
from qtos_core.portfolio import Portfolio
from qtos_core.strategy import Strategy
from qtos_core.risk import RiskManager

__all__ = [
    "Event",
    "EventLoop",
    "Signal",
    "Order",
    "Portfolio",
    "Strategy",
    "RiskManager",
]
