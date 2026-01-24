"""
Tests for trading strategies.
"""
import pytest
import pandas as pd
import numpy as np
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.strategies.base import Strategy
from src.strategies.rob_reversal import RobReversal


class TestRobReversalStrategy:
    """Tests for the RobReversal strategy."""

    def test_strategy_instantiation(self):
        """Test that RobReversal can be instantiated."""
        strategy = RobReversal()
        assert strategy is not None
        assert strategy.name == "RobReversal"

    def test_default_params(self):
        """Test that default params are set correctly."""
        strategy = RobReversal()
        assert 'ema_length' in strategy.default_params
        assert 'take_profit' in strategy.default_params
        assert 'max_stop_loss' in strategy.default_params
        assert strategy.default_params['ema_length'] == 8

    def test_get_params_with_override(self):
        """Test parameter override functionality."""
        strategy = RobReversal()
        custom_params = {'ema_length': 20, 'take_profit': 50.0}
        merged = strategy.get_params(custom_params)

        assert merged['ema_length'] == 20
        assert merged['take_profit'] == 50.0
        assert merged['max_stop_loss'] == strategy.default_params['max_stop_loss']

    def test_generate_signals_returns_correct_tuple_length(self, sample_ohlcv_data):
        """Test that generate_signals returns 6 elements."""
        strategy = RobReversal()
        result = strategy.generate_signals(sample_ohlcv_data)

        assert isinstance(result, tuple)
        assert len(result) == 6, "RobReversal should return 6 signals"

    def test_generate_signals_returns_series(self, sample_ohlcv_data):
        """Test that all returned signals are pandas Series."""
        strategy = RobReversal()
        long_entries, long_exits, short_entries, short_exits, exec_price, sl_dist = strategy.generate_signals(sample_ohlcv_data)

        assert isinstance(long_entries, pd.Series)
        assert isinstance(long_exits, pd.Series)
        assert isinstance(short_entries, pd.Series)
        assert isinstance(short_exits, pd.Series)
        assert isinstance(exec_price, pd.Series)
        assert isinstance(sl_dist, pd.Series)

    def test_generate_signals_correct_index(self, sample_ohlcv_data):
        """Test that signals have the same index as input data."""
        strategy = RobReversal()
        long_entries, _, _, _, _, _ = strategy.generate_signals(sample_ohlcv_data)

        assert len(long_entries) == len(sample_ohlcv_data)
        assert long_entries.index.equals(sample_ohlcv_data.index)

    def test_generate_signals_boolean_values(self, sample_ohlcv_data):
        """Test that entry/exit signals are boolean."""
        strategy = RobReversal()
        long_entries, long_exits, short_entries, short_exits, _, _ = strategy.generate_signals(sample_ohlcv_data)

        assert long_entries.dtype == bool
        assert long_exits.dtype == bool
        assert short_entries.dtype == bool
        assert short_exits.dtype == bool

    def test_strategy_with_custom_params(self, sample_ohlcv_data):
        """Test strategy execution with custom parameters."""
        strategy = RobReversal()
        custom_params = {
            'ema_length': 12,
            'take_profit': 40.0,
            'max_stop_loss': 30.0,
            'tick_size': 0.5
        }

        result = strategy.generate_signals(sample_ohlcv_data, custom_params)
        assert len(result) == 6


class TestStrategyBase:
    """Tests for the base Strategy class."""

    def test_strategy_is_abstract(self):
        """Test that Strategy cannot be instantiated directly."""
        with pytest.raises(TypeError):
            Strategy()

    def test_concrete_strategy_must_implement_generate_signals(self):
        """Test that subclasses must implement generate_signals."""
        class IncompleteStrategy(Strategy):
            pass

        with pytest.raises(TypeError):
            IncompleteStrategy()
