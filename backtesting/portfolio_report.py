"""
Portfolio report: print performance summary from BacktestResult and Metrics.
"""

from __future__ import annotations

from backtesting.engine import BacktestResult
from backtesting.metrics import Metrics, compute_metrics


def print_report(
    result: BacktestResult,
    initial_value: float,
    *,
    trading_days_per_year: int = 252,
    risk_free_rate: float = 0.0,
) -> Metrics:
    """
    Compute metrics from backtest result and print a performance summary.

    Parameters
    ----------
    result : BacktestResult
        Output of BacktestEngine.run().
    initial_value : float
        Starting portfolio value (e.g. initial cash).
    trading_days_per_year : int
        Used for CAGR/Sharpe (default 252).
    risk_free_rate : float
        Annual risk-free rate for Sharpe (default 0).

    Returns
    -------
    Metrics
        The computed metrics (e.g. for programmatic use).
    """
    metrics = compute_metrics(
        initial_value,
        result.equity_curve,
        trading_days_per_year=trading_days_per_year,
        risk_free_rate=risk_free_rate,
    )
    print("--- Backtest Performance ---")
    print(f"Initial value:    {metrics.initial_value:,.2f}")
    print(f"Final value:     {metrics.final_value:,.2f}")
    print(f"Total PnL:       {metrics.total_pnl:,.2f}")
    print(f"Total return:    {metrics.total_return_pct:.2f}%")
    print(f"CAGR:            {metrics.cagr:.2f}%")
    print(f"Sharpe ratio:    {metrics.sharpe_ratio:.2f}")
    print(f"Max drawdown:    {metrics.max_drawdown:,.2f} ({metrics.max_drawdown_pct:.2f}%)")
    print(f"Trades:          {len(result.trades)}")
    print("----------------------------")
    return metrics
