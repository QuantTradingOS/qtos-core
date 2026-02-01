"""
Modular backtesting framework on top of qtos-core.

Orchestrates market events through EventLoop; computes metrics; ready for
agent integration (Advisors, Validators, Observers).
"""

from backtesting.engine import BacktestEngine, BacktestResult, PassThroughRiskManager
from backtesting.data_loader import load_csv, load_dataframe
from backtesting.metrics import compute_metrics
from backtesting.portfolio_report import print_report

__all__ = [
    "BacktestEngine",
    "BacktestResult",
    "PassThroughRiskManager",
    "load_csv",
    "load_dataframe",
    "compute_metrics",
    "print_report",
]
