import pytest
import pandas as pd
import numpy as np
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.strategies.utbot_occ import UTBotOCC

class TestUTBotOCC:
    
    @pytest.fixture
    def sample_data(self):
        # Create a synthetic trend
        dates = pd.date_range(start='2023-01-01', periods=300, freq='15min')
        
        # Bull run then bear run
        closes = []
        val = 100.0
        for i in range(300):
            if i < 150:
                val += np.random.normal(0.2, 0.5) # Up with noise
            else:
                val -= np.random.normal(0.2, 0.5) # Down with noise
            closes.append(val)
            
        df = pd.DataFrame({
            'Open': [c - np.random.uniform(-1, 1) for c in closes],
            'High': [c + np.random.uniform(0.5, 2) for c in closes],
            'Low': [c - np.random.uniform(0.5, 2) for c in closes],
            'Close': closes,
            'Volume': 1000
        }, index=dates)
        return df

    def test_instantiation(self):
        strat = UTBotOCC()
        assert strat.name == "UTBotOCC"
        assert 'int_res' in strat.default_params
        assert 'occ_ma_length' not in strat.default_params
        assert 'key_value' in strat.default_params
        assert 'tick_buffer' in strat.default_params
        assert 'force_close_hour' in strat.default_params

    def test_generate_signals_returns_correct_shape(self, sample_data):
        strat = UTBotOCC()
        # Fast configuration to ensure it runs
        params = {
            'int_res': 7,
            'atr_period': 5,
            'ema_period': 10,
            'sl_lookback': 3
        }
        longs, exits_l, shorts, exits_s, execs, sls, ratios = strat.generate_signals(sample_data, params)
        
        assert len(longs) == len(sample_data)
        assert len(execs) == len(sample_data)
        assert isinstance(longs, pd.Series)
        assert isinstance(exits_l, pd.Series)
        assert isinstance(sls, pd.Series)

    def test_force_close_hour(self):
        """Test that force close happens at the specified hour."""
        dates = pd.date_range(start='2023-01-01 21:00:00', periods=10, freq='15min')
        
        df = pd.DataFrame({
            'Open': np.linspace(100, 110, 10),
            'High': np.linspace(101, 111, 10),
            'Low': np.linspace(99, 109, 10),
            'Close': np.linspace(100, 110, 10),
            'Volume': [1000]*10
        }, index=dates)
        
        strat = UTBotOCC()
        # Tight settings to trigger an entry fast
        params = {
            'int_res': 2,
            'lookback_entry': 5,
            'key_value': 0.1,
            'atr_period': 2,
            'force_close_hour': 22
        }
        longs, exits_l, shorts, exits_s, execs, sls, ratios = strat.generate_signals(df, params)
        
        # We just want to ensure it doesn't crash on hours check
        assert len(exits_l) == len(df)
        
    def test_empty_data(self):
        """Test with insufficient data."""
        df = pd.DataFrame({
            'Open': [100, 101],
            'High': [102, 103],
            'Low': [99, 100],
            'Close': [101, 102],
            'Volume': [1000, 1000]
        }, index=pd.date_range(start='2023-01-01', periods=2, freq='15min'))
        
        strat = UTBotOCC()
        longs, exits_l, shorts, exits_s, execs, sls, ratios = strat.generate_signals(df)
        
        # Should return all false/zeros/nans because length < min_length
        assert not longs.any()
        assert not exits_l.any()
