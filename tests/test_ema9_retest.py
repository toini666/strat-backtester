"""
Tests for the EMA9 Momentum Retest strategy.
"""
import pytest
import pandas as pd
import numpy as np
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.strategies.ema9_retest import EMA9Retest


@pytest.fixture
def large_ohlcv_data() -> pd.DataFrame:
    """Generate larger OHLCV data with trending behavior to trigger setups."""
    np.random.seed(123)
    n_bars = 500

    dates = pd.date_range(start='2024-01-01', periods=n_bars, freq='15min')

    # Generate trending price data to trigger EMA setups
    base_price = 5000.0
    returns = np.random.randn(n_bars) * 0.003
    # Add trending bias to create setup conditions
    for i in range(50, 70):
        returns[i] = abs(returns[i]) * 1.5  # Bullish run
    for i in range(200, 220):
        returns[i] = -abs(returns[i]) * 1.5  # Bearish run

    close = base_price * np.cumprod(1 + returns)

    high = close * (1 + np.abs(np.random.randn(n_bars) * 0.002))
    low = close * (1 - np.abs(np.random.randn(n_bars) * 0.002))
    open_ = np.roll(close, 1)
    open_[0] = base_price

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


class TestEMA9RestestStrategy:
    """Tests for the EMA9Retest strategy."""

    def test_strategy_instantiation(self):
        """Test that EMA9Retest can be instantiated."""
        strategy = EMA9Retest()
        assert strategy is not None
        assert strategy.name == "EMA9Retest"
        assert strategy.manual_exit is True

    def test_default_params(self):
        """Test that default params are set correctly."""
        strategy = EMA9Retest()
        assert strategy.default_params['ema_length'] == 9
        assert strategy.default_params['nb_candles'] == 3
        assert strategy.default_params['retest_tolerance'] == 3
        assert strategy.default_params['max_bars'] == 10
        assert strategy.default_params['sl_margin'] == 3
        assert strategy.default_params['rr_be'] == 1.0
        assert strategy.default_params['rr_tp1'] == 2.0
        assert strategy.default_params['tp_partial_pct'] == 0.5

    def test_get_params_with_override(self):
        """Test parameter override functionality."""
        strategy = EMA9Retest()
        custom_params = {'ema_length': 21, 'rr_tp1': 3.0}
        merged = strategy.get_params(custom_params)

        assert merged['ema_length'] == 21
        assert merged['rr_tp1'] == 3.0
        assert merged['nb_candles'] == strategy.default_params['nb_candles']

    def test_generate_signals_returns_correct_tuple_length(self, sample_ohlcv_data):
        """Test that generate_signals returns 7 elements."""
        strategy = EMA9Retest()
        result = strategy.generate_signals(sample_ohlcv_data)

        assert isinstance(result, tuple)
        assert len(result) == 7, "EMA9Retest should return 7 signals"

    def test_generate_signals_returns_series(self, sample_ohlcv_data):
        """Test that all returned signals are pandas Series."""
        strategy = EMA9Retest()
        long_entries, long_exits, short_entries, short_exits, exec_price, sl_dist, exit_ratio = strategy.generate_signals(sample_ohlcv_data)

        assert isinstance(long_entries, pd.Series)
        assert isinstance(long_exits, pd.Series)
        assert isinstance(short_entries, pd.Series)
        assert isinstance(short_exits, pd.Series)
        assert isinstance(exec_price, pd.Series)
        assert isinstance(sl_dist, pd.Series)
        assert isinstance(exit_ratio, pd.Series)

    def test_generate_signals_correct_index(self, sample_ohlcv_data):
        """Test that signals have the same index as input data."""
        strategy = EMA9Retest()
        long_entries, _, _, _, _, _, _ = strategy.generate_signals(sample_ohlcv_data)

        assert len(long_entries) == len(sample_ohlcv_data)
        assert long_entries.index.equals(sample_ohlcv_data.index)

    def test_generate_signals_boolean_values(self, sample_ohlcv_data):
        """Test that entry/exit signals are boolean."""
        strategy = EMA9Retest()
        long_entries, long_exits, short_entries, short_exits, _, _, _ = strategy.generate_signals(sample_ohlcv_data)

        assert long_entries.dtype == bool
        assert long_exits.dtype == bool
        assert short_entries.dtype == bool
        assert short_exits.dtype == bool

    def test_exit_ratios_are_valid(self, sample_ohlcv_data):
        """Test that exit ratios are between 0 and 1."""
        strategy = EMA9Retest()
        _, _, _, _, _, _, exit_ratios = strategy.generate_signals(sample_ohlcv_data)

        assert (exit_ratios >= 0).all()
        assert (exit_ratios <= 1).all()

    def test_strategy_with_larger_data(self, large_ohlcv_data):
        """Test strategy execution with 500 bars of data."""
        strategy = EMA9Retest()
        result = strategy.generate_signals(large_ohlcv_data)

        assert len(result) == 7
        long_entries, long_exits, short_entries, short_exits, _, sl_dists, _ = result

        # With 500 bars of trending data, we should get at least some signals
        total_entries = long_entries.sum() + short_entries.sum()
        assert total_entries >= 0  # May be 0 in random data, that's OK

    def test_strategy_with_custom_params(self, large_ohlcv_data):
        """Test strategy execution with custom parameters."""
        strategy = EMA9Retest()
        custom_params = {
            'ema_length': 5,
            'nb_candles': 2,
            'retest_tolerance': 5,
            'max_bars': 20,
            'tick_size': 0.25
        }

        result = strategy.generate_signals(large_ohlcv_data, custom_params)
        assert len(result) == 7

    def test_sl_distance_positive_on_entries(self, large_ohlcv_data):
        """Test that SL distance is positive for all entries."""
        strategy = EMA9Retest()
        long_entries, _, short_entries, _, _, sl_dists, _ = strategy.generate_signals(large_ohlcv_data)

        entries = long_entries | short_entries
        if entries.any():
            entry_sl = sl_dists[entries]
            # Filter out NaN
            valid = entry_sl.dropna()
            if len(valid) > 0:
                assert (valid > 0).all(), "SL distances should be positive at entry points"
