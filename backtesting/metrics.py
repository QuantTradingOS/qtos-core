"""
Backtest metrics: PnL, Sharpe ratio, drawdown, CAGR.

Uses equity curve and initial/final portfolio value. Annualization assumes 252 trading days.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Sequence

import numpy as np


@dataclass
class Metrics:
    """Standard backtest performance metrics."""

    initial_value: float
    final_value: float
    total_pnl: float
    total_return_pct: float
    cagr: float
    sharpe_ratio: float
    max_drawdown: float
    max_drawdown_pct: float


def compute_metrics(
    initial_value: float,
    equity_curve: Sequence[tuple[datetime, float]],
    *,
    trading_days_per_year: int = 252,
    risk_free_rate: float = 0.0,
) -> Metrics:
    """
    Compute performance metrics from initial capital and equity curve.

    Parameters
    ----------
    initial_value : float
        Starting portfolio value.
    equity_curve : sequence of (datetime, value)
        Time-ordered (timestamp, portfolio value) pairs.
    trading_days_per_year : int
        Used for annualizing returns and Sharpe (default 252).
    risk_free_rate : float
        Annual risk-free rate for Sharpe (default 0).

    Returns
    -------
    Metrics
        final_value, total_pnl, total_return_pct, cagr, sharpe_ratio,
        max_drawdown, max_drawdown_pct.
    """
    if not equity_curve:
        return Metrics(
            initial_value=initial_value,
            final_value=initial_value,
            total_pnl=0.0,
            total_return_pct=0.0,
            cagr=0.0,
            sharpe_ratio=0.0,
            max_drawdown=0.0,
            max_drawdown_pct=0.0,
        )

    values = np.array([v for _, v in equity_curve], dtype=float)
    final_value = float(values[-1])
    total_pnl = final_value - initial_value
    total_return_pct = (total_pnl / initial_value * 100.0) if initial_value else 0.0

    # CAGR: (final/initial)^(years) - 1
    n = len(values)
    if n < 2:
        years = 1e-10
    else:
        t0 = equity_curve[0][0]
        t1 = equity_curve[-1][0]
        if hasattr(t0, "to_pydatetime"):
            t0 = t0.to_pydatetime()
        if hasattr(t1, "to_pydatetime"):
            t1 = t1.to_pydatetime()
        days = (t1 - t0).total_seconds() / 86400.0 if hasattr(t0, "__sub__") else n
        years = max(days / trading_days_per_year, 1e-10)
    cagr = (final_value / initial_value) ** (1.0 / years) - 1.0 if initial_value > 0 else 0.0
    cagr *= 100.0  # as percentage

    # Daily returns for Sharpe
    returns = np.diff(values) / np.maximum(values[:-1], 1e-14)
    if len(returns) == 0:
        sharpe_ratio = 0.0
    else:
        excess = returns - (risk_free_rate / trading_days_per_year)
        std = np.std(excess)
        sharpe_ratio = (np.mean(excess) / std * np.sqrt(trading_days_per_year)) if std > 1e-14 else 0.0

    # Max drawdown
    peak = np.maximum.accumulate(values)
    drawdowns = peak - values
    max_drawdown = float(np.max(drawdowns))
    max_dd_pct = (max_drawdown / peak[np.argmax(drawdowns)] * 100.0) if np.any(peak > 0) else 0.0

    return Metrics(
        initial_value=initial_value,
        final_value=final_value,
        total_pnl=total_pnl,
        total_return_pct=total_return_pct,
        cagr=cagr,
        sharpe_ratio=sharpe_ratio,
        max_drawdown=max_drawdown,
        max_drawdown_pct=max_dd_pct,
    )
