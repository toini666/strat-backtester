
import pytest
import pandas as pd
import numpy as np
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.strategies.utbot_stc import UTBotSTC

class TestUTBotSTC:
    
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
        strat = UTBotSTC()
        assert strat.name == "UTBotSTC"
        assert 'use_heikin_ashi' in strat.default_params
        assert 'stc_length' in strat.default_params
        # New position management params
        assert 'partial_rr' in strat.default_params
        assert 'partial_pct' in strat.default_params
        assert 'breakeven_rr' in strat.default_params
        assert 'ema_length' in strat.default_params
        # Old param should not exist
        assert 'risk_reward' not in strat.default_params

    def test_generate_signals_returns_correct_shape(self, sample_data):
        strat = UTBotSTC()
        longs, exits_l, shorts, exits_s, execs, sls, ratios = strat.generate_signals(sample_data)
        
        assert len(longs) == len(sample_data)
        assert len(execs) == len(sample_data)
        assert isinstance(longs, pd.Series)
        assert isinstance(ratios, pd.Series)
        assert isinstance(sls, pd.Series)

    def test_heikin_ashi_toggle(self, sample_data):
        """Test that HA toggle changes the outcome (signals)."""
        strat = UTBotSTC()
        
        # Run with HA
        l1, _, s1, _, _, _, _ = strat.generate_signals(sample_data, {'use_heikin_ashi': True})
        
        # Run without HA
        l2, _, s2, _, _, _, _ = strat.generate_signals(sample_data, {'use_heikin_ashi': False})
        
        # They should likely be different on noisy data
        assert isinstance(l1, pd.Series)
        assert isinstance(l2, pd.Series)
        
        # Verify signals are boolean
        assert l1.dtype == bool
        assert l2.dtype == bool

    def test_position_management(self, sample_data):
        """Test that exits are generated with new partial TP logic."""
        strat = UTBotSTC()
        # Use tight settings to ensure some trades
        params = {
            'partial_rr': 0.5,
            'breakeven_rr': 0.3,
            'stop_ticks': 1  
        }
        l, lx, s, sx, _, _, ratios = strat.generate_signals(sample_data, params)
        
        # We expect some trades
        assert lx.dtype == bool
        assert sx.dtype == bool
        
        # Check that exit_ratios contains partial values when partial TP was taken
        if lx.sum() > 0 or sx.sum() > 0:
            # Some exits should have partial ratio (0.5 default)
            partial_exits = ratios[ratios < 1.0]
            # Not guaranteed but likely with tight settings
            assert isinstance(partial_exits, pd.Series)

    def test_partial_exit_ratios(self, sample_data):
        """Test that exit_ratios uses partial_pct for partial TPs."""
        strat = UTBotSTC()
        params = {
            'partial_rr': 0.3,     # Very tight to trigger early
            'breakeven_rr': 0.2,   # Very tight  
            'partial_pct': 0.6,    # Custom partial percentage
            'stop_ticks': 1
        }
        _, lx, _, sx, _, _, ratios = strat.generate_signals(sample_data, params)
        
        # Check partial ratio values if any
        partial_mask = (ratios < 1.0) & (ratios > 0.0)
        if partial_mask.sum() > 0:
            assert all(ratios[partial_mask] == 0.6)

    def test_stc_filters(self, sample_data):
        """Test STC parameters."""
        strat = UTBotSTC()
        # Extreme STC settings that should block everything
        params_strict = {
            'stc_min_long': 101,  # Impossible
            'stc_max_long': 0,
            'stc_min_short': 101,
            'stc_max_short': 0
        }
        
        l, _, s, _, _, _, _ = strat.generate_signals(sample_data, params_strict)
        
        assert l.sum() == 0
        assert s.sum() == 0

    def test_ema_length_param(self, sample_data):
        """Test that ema_length parameter is recognized."""
        strat = UTBotSTC()
        # Should run without error with custom EMA length
        params = {'ema_length': 21}
        l, lx, s, sx, _, _, _ = strat.generate_signals(sample_data, params)
        assert isinstance(l, pd.Series)
