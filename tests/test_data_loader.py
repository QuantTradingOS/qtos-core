"""
Tests for backtesting data_loader: load_csv, load_dataframe.
"""

from pathlib import Path

import pandas as pd
import pytest

from backtesting.data_loader import load_csv, load_dataframe


def test_load_dataframe_normalizes_columns():
    df = pd.DataFrame({
        "Date": ["2024-01-01", "2024-01-02"],
        "Open": [100.0, 101.0],
        "High": [102.0, 103.0],
        "Low": [99.0, 100.0],
        "Close": [101.0, 102.0],
        "Volume": [1e6, 1e6],
    })
    out = load_dataframe(df, datetime_index="Date", symbol="SPY")
    assert "open" in out.columns
    assert "high" in out.columns
    assert "low" in out.columns
    assert "close" in out.columns
    assert "volume" in out.columns
    assert isinstance(out.index, pd.DatetimeIndex)
    assert out.index.name == "datetime"
    assert out.attrs.get("symbol") == "SPY"


def test_load_dataframe_aliases():
    df = pd.DataFrame({
        "datetime": pd.date_range("2024-01-01", periods=3, freq="D"),
        "o": [100.0, 101.0, 102.0],
        "h": [101.0, 102.0, 103.0],
        "l": [99.0, 100.0, 101.0],
        "c": [100.5, 101.5, 102.5],
        "vol": [1e6, 1e6, 1e6],
    }).set_index("datetime")
    out = load_dataframe(df, symbol="QQQ")
    assert "open" in out.columns
    assert "close" in out.columns
    assert "volume" in out.columns
    assert out.attrs.get("symbol") == "QQQ"


def test_load_csv_uses_sample_data():
    """Use the existing sample CSV in examples/data if present."""
    csv_path = Path(__file__).resolve().parent.parent / "examples" / "data" / "sample_ohlcv.csv"
    if not csv_path.exists():
        pytest.skip("sample_ohlcv.csv not found")
    df = load_csv(csv_path, symbol="SPY")
    assert not df.empty
    assert "close" in df.columns
    assert isinstance(df.index, pd.DatetimeIndex)
    assert df.attrs.get("symbol") == "SPY"
