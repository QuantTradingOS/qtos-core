"""
Execution layer: broker abstraction and paper/live execution.

BrokerAdapter interface; paper trading adapter; safety (PnL limit, max size, kill switch).
Agent hooks: Advisors, Validators, Observers (compatible with backtesting protocols).
"""

from qtos_core.execution.broker import BrokerAdapter
from qtos_core.execution.paper import PaperBrokerAdapter
from qtos_core.execution.engine import ExecutionEngine, RejectedOrderLog
from qtos_core.execution.types import ExecutedTrade, OrderStatus, OrderStatusKind, PortfolioState

__all__ = [
    "BrokerAdapter",
    "OrderStatus",
    "OrderStatusKind",
    "PortfolioState",
    "PaperBrokerAdapter",
    "ExecutionEngine",
    "ExecutedTrade",
    "RejectedOrderLog",
]
