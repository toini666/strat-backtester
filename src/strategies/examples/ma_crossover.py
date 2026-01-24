from ..base import Strategy
import pandas as pd
import pandas_ta_classic as ta

class MACrossover(Strategy):
    """
    Moving Average Crossover Strategy.
    
    Long: Fast MA crosses above Slow MA
    Exit: Fast MA crosses below Slow MA
    """
    
    name = "MA Crossover"
    
    default_params = {
        "fast_period": 10,
        "slow_period": 50,
        "ma_type": "EMA", # SMA, EMA
        "stop_loss_pct": 0.02
    }
    
    param_ranges = {
        "fast_period": range(5, 30, 5),
        "slow_period": range(20, 100, 10),
        "stop_loss_pct": [0.01, 0.02, 0.03, 0.05]
    }
    
    def generate_signals(self, data: pd.DataFrame, params: dict = None):
        p = self.get_params(params)
        
        # Calculate indicators
        if p["ma_type"] == "EMA":
            fast = data.ta.ema(length=p["fast_period"])
            slow = data.ta.ema(length=p["slow_period"])
        else:
            fast = data.ta.sma(length=p["fast_period"])
            slow = data.ta.sma(length=p["slow_period"])
            
        # Generate signals
        # Entry: Fast > Slow AND Prev(Fast) <= Prev(Slow)
        entries = (fast > slow) & (fast.shift(1) <= slow.shift(1))
        
        # Exit: Fast < Slow AND Prev(Fast) >= Prev(Slow)
        exits = (fast < slow) & (fast.shift(1) >= slow.shift(1))
        
        return entries, exits
        
    def get_stop_loss(self, data, entry_idx, params=None):
        p = self.get_params(params)
        entry_price = data['Close'].iloc[entry_idx]
        return entry_price * (1 - p["stop_loss_pct"])
