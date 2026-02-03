"""
Tests for the Brochettes strategy.
"""
import pytest
import pandas as pd
import numpy as np
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.strategies.brochettes import Brochettes
from src.strategies.base import Strategy


class TestBrochettesStrategy:
    """Tests for the Brochettes strategy."""

    def test_strategy_instantiation(self):
        """Test that Brochettes can be instantiated."""
        strategy = Brochettes()
        assert strategy is not None
        assert strategy.name == "Brochettes"

    def test_inherits_from_strategy(self):
        """Test that Brochettes inherits from Strategy base class."""
        strategy = Brochettes()
        assert isinstance(strategy, Strategy)

    def test_default_params(self):
        """Test that default params are set correctly."""
        strategy = Brochettes()
        assert 'risk_reward' in strategy.default_params
        assert 'use_filter' in strategy.default_params
        assert 'filter_method' in strategy.default_params
        assert 'filter_lookback' in strategy.default_params
        assert 'filter_threshold' in strategy.default_params
        
        # Check default values
        assert strategy.default_params['risk_reward'] == 2.0
        assert strategy.default_params['use_filter'] == True
        assert strategy.default_params['filter_method'] == "slope"
        assert strategy.default_params['filter_lookback'] == 5
        assert strategy.default_params['filter_threshold'] == 2.0
        
        # Alligator params
        assert strategy.default_params['jaw_length'] == 13
        assert strategy.default_params['teeth_length'] == 8
        assert strategy.default_params['lips_length'] == 5

    def test_param_ranges(self):
        """Test that optimization param ranges are defined."""
        strategy = Brochettes()
        assert 'risk_reward' in strategy.param_ranges
        assert 'use_filter' in strategy.param_ranges
        assert 'filter_method' in strategy.param_ranges
        assert 'filter_lookback' in strategy.param_ranges
        assert 'filter_threshold' in strategy.param_ranges

    def test_get_params_with_override(self):
        """Test parameter override functionality."""
        strategy = Brochettes()
        custom_params = {'risk_reward': 3.0, 'use_filter': False}
        merged = strategy.get_params(custom_params)

        assert merged['risk_reward'] == 3.0
        assert merged['use_filter'] == False
        # Unchanged params should retain defaults
        assert merged['filter_lookback'] == strategy.default_params['filter_lookback']

    def test_generate_signals_returns_correct_tuple_length(self, sample_ohlcv_data):
        """Test that generate_signals returns 6 elements."""
        strategy = Brochettes()
        result = strategy.generate_signals(sample_ohlcv_data)

        assert isinstance(result, tuple)
        assert len(result) == 6, "Brochettes should return 6 signals"

    def test_generate_signals_returns_series(self, sample_ohlcv_data):
        """Test that all returned signals are pandas Series."""
        strategy = Brochettes()
        long_entries, long_exits, short_entries, short_exits, exec_price, sl_dist = strategy.generate_signals(sample_ohlcv_data)

        assert isinstance(long_entries, pd.Series)
        assert isinstance(long_exits, pd.Series)
        assert isinstance(short_entries, pd.Series)
        assert isinstance(short_exits, pd.Series)
        assert isinstance(exec_price, pd.Series)
        assert isinstance(sl_dist, pd.Series)

    def test_generate_signals_correct_index(self, sample_ohlcv_data):
        """Test that signals have the same index as input data."""
        strategy = Brochettes()
        long_entries, _, _, _, _, _ = strategy.generate_signals(sample_ohlcv_data)

        assert len(long_entries) == len(sample_ohlcv_data)
        assert long_entries.index.equals(sample_ohlcv_data.index)

    def test_generate_signals_boolean_values(self, sample_ohlcv_data):
        """Test that entry/exit signals are boolean."""
        strategy = Brochettes()
        long_entries, long_exits, short_entries, short_exits, _, _ = strategy.generate_signals(sample_ohlcv_data)

        assert long_entries.dtype == bool
        assert long_exits.dtype == bool
        assert short_entries.dtype == bool
        assert short_exits.dtype == bool

    def test_strategy_with_filter_disabled(self, sample_ohlcv_data):
        """Test strategy execution with filter disabled."""
        strategy = Brochettes()
        custom_params = {'use_filter': False}

        result = strategy.generate_signals(sample_ohlcv_data, custom_params)
        assert len(result) == 6

    def test_strategy_with_spread_method(self, sample_ohlcv_data):
        """Test strategy with spread filter method."""
        strategy = Brochettes()
        custom_params = {'filter_method': 'spread'}

        result = strategy.generate_signals(sample_ohlcv_data, custom_params)
        assert len(result) == 6

    def test_smma_calculation(self):
        """Test SMMA calculation matches expected behavior."""
        strategy = Brochettes()
        
        # Create simple test data
        test_series = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0])
        smma = strategy._smma(test_series, 3)
        
        # First valid value should be SMA of first 3 elements
        expected_first = (1.0 + 2.0 + 3.0) / 3  # = 2.0
        assert smma.iloc[2] == expected_first
        
        # Subsequent values follow SMMA formula
        expected_second = (expected_first * 2 + 4.0) / 3
        assert abs(smma.iloc[3] - expected_second) < 0.0001

    def test_manual_exit_flag(self):
        """Test that manual_exit is set to True."""
        strategy = Brochettes()
        assert strategy.manual_exit == True
