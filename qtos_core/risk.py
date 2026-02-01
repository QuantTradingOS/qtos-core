"""
RiskManager: interface for order approval/modification.

Consumes an order (or signal) and portfolio; returns approved order(s) or none.
Implementations define limits and rules; the engine enforces the interface.
"""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from qtos_core.order import Order
    from qtos_core.portfolio import Portfolio
    from qtos_core.signal import Signal


class RiskManager(ABC):
    """
    Base class for risk managers. Approve, reject, or modify orders
    before they are considered by the engine (e.g. for fills).
    """

    @abstractmethod
    def check(
        self,
        signal_or_order: "Signal | Order",
        portfolio: "Portfolio",
    ) -> "Order | None":
        """
        Check signal/order against risk rules. Return an Order to allow,
        or None to reject. May modify size or type.
        """
        ...
