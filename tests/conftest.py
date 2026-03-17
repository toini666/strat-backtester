"""
Pytest configuration and fixtures for Nebular Apollo tests.
"""
import sys
import os
from datetime import datetime, timedelta

import pytest
import pandas as pd
import numpy as np

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


@pytest.fixture
def sample_ohlcv_data() -> pd.DataFrame:
    """Generate sample OHLCV data for testing."""
    np.random.seed(42)
    n_bars = 100

    dates = pd.date_range(start='2024-01-01', periods=n_bars, freq='15min')

    # Generate realistic price data
    base_price = 100.0
    returns = np.random.randn(n_bars) * 0.002  # 0.2% volatility
    close = base_price * np.cumprod(1 + returns)

    # Generate OHLC from close
    high = close * (1 + np.abs(np.random.randn(n_bars) * 0.001))
    low = close * (1 - np.abs(np.random.randn(n_bars) * 0.001))
    open_ = np.roll(close, 1)
    open_[0] = base_price

    # Ensure High >= max(Open, Close) and Low <= min(Open, Close)
    high = np.maximum(high, np.maximum(open_, close))
    low = np.minimum(low, np.minimum(open_, close))

    volume = np.random.randint(1000, 10000, n_bars)

    df = pd.DataFrame({
        'Open': open_,
        'High': high,
        'Low': low,
        'Close': close,
        'Volume': volume
    }, index=dates)

    return df


@pytest.fixture
def sample_backtest_request() -> dict:
    """Sample backtest request payload."""
    return {
        "strategy_name": "EMABreakOsc",
        "symbol": "MNQ",
        "interval": "15m",
        "start_datetime": "2026-02-01T00:00",
        "end_datetime": "2026-03-01T00:00",
        "params": {},
        "initial_equity": 50000.0,
        "risk_per_trade": 0.01
    }


@pytest.fixture
def empty_dataframe() -> pd.DataFrame:
    """Return an empty DataFrame with OHLCV columns."""
    return pd.DataFrame(columns=['Open', 'High', 'Low', 'Close', 'Volume'])
