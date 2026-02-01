"""
Load historical price data from CSV or DataFrame for backtesting.

Expects datetime index and OHLC(V) columns. Symbol can be inferred or passed.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd


# Standard column names; lowercase for normalization
OHLCV = ("open", "high", "low", "close", "volume")
OHLC = ("open", "high", "low", "close")


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Ensure columns are lowercase; map common aliases to open/high/low/close/volume."""
    out = df.copy()
    out.columns = [str(c).lower().strip() for c in out.columns]
    # Common aliases
    renames = {
        "o": "open",
        "h": "high",
        "l": "low",
        "c": "close",
        "v": "volume",
        "vol": "volume",
    }
    out = out.rename(columns={k: v for k, v in renames.items() if k in out.columns})
    return out


def load_csv(
    path: str | Path,
    *,
    date_column: str | None = None,
    datetime_format: str | None = None,
    symbol: str | None = None,
) -> pd.DataFrame:
    """
    Load OHLC(V) data from a CSV file.

    Parameters
    ----------
    path : str or Path
        Path to the CSV file.
    date_column : str, optional
        Column to use as datetime index. If None, first column or 'date' is used.
    datetime_format : str, optional
        Format for parsing dates (e.g. '%Y-%m-%d').
    symbol : str, optional
        Symbol to attach (stored in df.attrs['symbol'] if provided).

    Returns
    -------
    pd.DataFrame
        DataFrame with DatetimeIndex and columns open, high, low, close, and
        optionally volume. Index name is 'datetime'.
    """
    df = pd.read_csv(path)
    df = _normalize_columns(df)
    date_col = date_column or ("date" if "date" in df.columns else df.columns[0])
    if date_col not in df.columns:
        date_col = df.columns[0]
    df["datetime"] = pd.to_datetime(df[date_col], format=datetime_format)
    df = df.drop(columns=[date_col], errors="ignore")
    df = df.set_index("datetime").sort_index()
    keep = [c for c in OHLCV if c in df.columns]
    df = df[[c for c in df.columns if c in keep]]
    df.index.name = "datetime"
    if symbol is not None:
        df.attrs["symbol"] = symbol
    return df


def load_dataframe(
    df: pd.DataFrame,
    *,
    datetime_index: str | None = None,
    symbol: str | None = None,
) -> pd.DataFrame:
    """
    Normalize a DataFrame for backtesting: DatetimeIndex and OHLC(V) columns.

    Parameters
    ----------
    df : pd.DataFrame
        Raw DataFrame (columns may be mixed case or aliased).
    datetime_index : str, optional
        Column name to use as index. If None, assume index is already datetime.
    symbol : str, optional
        Symbol to store in df.attrs['symbol'].

    Returns
    -------
    pd.DataFrame
        Normalized DataFrame with DatetimeIndex and open, high, low, close, [volume].
    """
    out = _normalize_columns(df.copy())
    if datetime_index is not None and datetime_index in out.columns:
        out["datetime"] = pd.to_datetime(out[datetime_index])
        out = out.set_index("datetime").sort_index()
    elif not isinstance(out.index, pd.DatetimeIndex):
        out.index = pd.to_datetime(out.index)
        out = out.sort_index()
    out.index.name = "datetime"
    keep = [c for c in OHLCV if c in out.columns]
    out = out[[c for c in out.columns if c in keep]]
    if symbol is not None:
        out.attrs["symbol"] = symbol
    return out
