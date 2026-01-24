from ..base import Strategy
import pandas as pd
import pandas_ta_classic as ta

class RSIReversal(Strategy):
    """
    RSI Mean Reversal Strategy.
    
    Long: RSI crosses below lower threshold (oversold)
    Exit: RSI crosses above upper threshold (overbought)
    """
    
    name = "RSI Reversal"
    
    default_params = {
        "rsi_period": 14,
        "rsi_lower": 30,
        "rsi_upper": 70,
        "stop_loss_pct": 0.03
    }
    
    param_ranges = {
        "rsi_period": [7, 14, 21],
        "rsi_lower": [20, 25, 30, 35],
        "rsi_upper": [65, 70, 75, 80]
    }
    
    def generate_signals(self, data: pd.DataFrame, params: dict = None):
        p = self.get_params(params)
        
        # Calculate RSI
        rsi = data.ta.rsi(length=p["rsi_period"])
        
        # Entry: Cross below lower (buy signal)
        entries = (rsi < p["rsi_lower"]) & (rsi.shift(1) >= p["rsi_lower"])
        
        # Exit: Cross above upper (sell signal)
        exits = (rsi > p["rsi_upper"]) & (rsi.shift(1) <= p["rsi_upper"])
        
        return entries, exits

    def get_stop_loss(self, data, entry_idx, params=None):
        p = self.get_params(params)
        entry_price = data['Close'].iloc[entry_idx]
        return entry_price * (1 - p["stop_loss_pct"])
