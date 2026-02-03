from .base import Strategy
import pandas as pd
import numpy as np
from typing import Tuple, Dict, Any


class Brochettes(Strategy):
    """
    Brochettes Strategy 🍢
    Based on the Alligator/Crocodile indicator by Bill Williams.
    
    Logic:
    - Uses SMMA for Jaw (13), Teeth (8), Lips (5) with offsets (8, 5, 3)
    - Brochette Bear: Bearish candle where open > all 3 lines AND close < all 3 lines
    - Brochette Bull: Bullish candle where open < all 3 lines AND close > all 3 lines
    - Entry: At close of signal candle (executed on next bar)
    - Stop Loss: High (SELL) or Low (BUY) of signal candle
    - Take Profit: Entry ± (SL distance × Risk/Reward)
    
    Optional Range Filter:
    - Slope: |jaw - jaw[lookback]| / tick_size
    - Spread: |jaw - lips| / tick_size
    - If value < threshold, market is flat → ignore signals
    """
    
    name = "Brochettes"
    manual_exit = True
    
    default_params = {
        # Alligator settings (fixed per user request)
        "jaw_length": 13,
        "teeth_length": 8,
        "lips_length": 5,
        "jaw_offset": 8,
        "teeth_offset": 5,
        "lips_offset": 3,
        # Risk Management
        "risk_reward": 2.0,
        # Range Filter
        "use_filter": True,
        "filter_method": "slope",  # "slope" or "spread"
        "filter_lookback": 5,
        "filter_threshold": 2.0,
        # Trade Management
        "tick_size": 0.25,
        "block_new_signals": True
    }

    # Parameter ranges for optimization (only user-requested params)
    param_ranges = {
        "risk_reward": [1.0, 1.5, 2.0, 2.5, 3.0],
        "use_filter": [True, False],
        "filter_method": ["slope", "spread"],
        "filter_lookback": [3, 5, 8, 10],
        "filter_threshold": [1.0, 2.0, 3.0, 5.0],
    }

    def _smma(self, series: pd.Series, length: int) -> pd.Series:
        """
        Calculate Smoothed Moving Average (SMMA) - same as Pine Script.
        SMMA formula: smma[i] = (smma[i-1] * (length - 1) + src[i]) / length
        First value is SMA.
        """
        smma = pd.Series(index=series.index, dtype=float)
        
        # First value: SMA
        smma.iloc[length - 1] = series.iloc[:length].mean()
        
        # Subsequent values: SMMA formula
        for i in range(length, len(series)):
            smma.iloc[i] = (smma.iloc[i - 1] * (length - 1) + series.iloc[i]) / length
            
        return smma

    def generate_signals(
        self, 
        data: pd.DataFrame, 
        params: Dict[str, Any] = None
    ) -> Tuple[pd.Series, pd.Series, pd.Series, pd.Series, pd.Series, pd.Series]:
        p = self.get_params(params)
        
        close = data['Close']
        open_ = data['Open']
        high = data['High']
        low = data['Low']
        
        # hl2 = (high + low) / 2 - same as Pine Script
        hl2 = (high + low) / 2
        
        # Calculate Alligator lines using SMMA
        jaw = self._smma(hl2, p['jaw_length'])
        teeth = self._smma(hl2, p['teeth_length'])
        lips = self._smma(hl2, p['lips_length'])
        
        # Apply offsets (shift forward = access past values for current comparison)
        # In Pine: jaw[jawOffset] means "jaw value from jawOffset bars ago"
        jaw_offset = jaw.shift(p['jaw_offset'])
        teeth_offset = teeth.shift(p['teeth_offset'])
        lips_offset = lips.shift(p['lips_offset'])
        
        # Range Filter calculation
        ts_tick = p['tick_size']
        
        if p['filter_method'] == "slope":
            # Slope: |jaw - jaw[lookback]| / tick
            filter_value = (jaw - jaw.shift(p['filter_lookback'])).abs() / ts_tick
        else:
            # Spread: |jaw - lips| / tick
            filter_value = (jaw - lips).abs() / ts_tick
        
        is_market_flat = p['use_filter'] & (filter_value < p['filter_threshold'])
        
        # Brochette detection
        # Bear: Bearish candle (open > close) that pierces all 3 lines from above to below
        brochette_bear = (
            (open_ > close) &  # Bearish candle
            (open_ > jaw_offset) & (open_ > teeth_offset) & (open_ > lips_offset) &  # Open above all
            (close < jaw_offset) & (close < teeth_offset) & (close < lips_offset)    # Close below all
        )
        
        # Bull: Bullish candle (open < close) that pierces all 3 lines from below to above
        brochette_bull = (
            (open_ < close) &  # Bullish candle
            (open_ < jaw_offset) & (open_ < teeth_offset) & (open_ < lips_offset) &  # Open below all
            (close > jaw_offset) & (close > teeth_offset) & (close > lips_offset)    # Close above all
        )
        
        # Output signals
        long_entries = pd.Series(False, index=data.index)
        long_exits = pd.Series(False, index=data.index)
        short_entries = pd.Series(False, index=data.index)
        short_exits = pd.Series(False, index=data.index)
        
        # NumPy arrays for speed
        np_high = high.values
        np_low = low.values
        np_close = close.values
        np_open = open_.values
        np_brochette_bear = brochette_bear.fillna(False).values
        np_brochette_bull = brochette_bull.fillna(False).values
        np_is_flat = is_market_flat.fillna(False).values
        
        # State
        pending_entry_price = 0.0
        pending_sl = 0.0
        pending_tp = 0.0
        pending_side = 0  # 0=None, 1=Long, -1=Short
        
        active_trade_side = 0  # 1=Long, -1=Short, 0=None
        active_tp = 0.0
        active_sl = 0.0
        
        block_new = p['block_new_signals']
        rr = p['risk_reward']

        def round_to_tick(price, tick_size):
            return round(price / tick_size) * tick_size

        # SL Distance Series (for dynamic sizing)
        np_sl_dist = np.full(len(data), np.nan)
        
        # Execution Price Series
        np_exec_price = np_close.copy()

        for i in range(len(data)):
            trade_closed_this_bar = False
            did_enter = False
            
            O = np_open[i]
            H = np_high[i]
            L = np_low[i]
            C = np_close[i]
            
            # --- 1. EXECUTE PENDING ENTRY ---
            # Entry happens at close of signal bar (which is now "this bar's open" from perspective of next bar)
            # But since we store pending from previous bar, we enter at the OPEN of this bar
            if active_trade_side == 0 and pending_side != 0:
                # Enter position
                if pending_side == 1:
                    long_entries.iloc[i] = True
                    np_exec_price[i] = pending_entry_price
                    active_trade_side = 1
                    active_tp = pending_tp
                    active_sl = pending_sl
                    np_sl_dist[i] = pending_entry_price - pending_sl
                    did_enter = True
                elif pending_side == -1:
                    short_entries.iloc[i] = True
                    np_exec_price[i] = pending_entry_price
                    active_trade_side = -1
                    active_tp = pending_tp
                    active_sl = pending_sl
                    np_sl_dist[i] = pending_sl - pending_entry_price
                    did_enter = True
                
                # Clear pending
                pending_side = 0
                pending_entry_price = 0.0
                pending_sl = 0.0
                pending_tp = 0.0
            
            # --- 2. MANAGE ACTIVE POSITION (SL/TP) ---
            if active_trade_side == 1:  # Long position
                hit_sl = L <= active_sl
                hit_tp = H >= active_tp
                
                if hit_sl or hit_tp:
                    if hit_sl and hit_tp:
                        # Both hit - determine which first based on open proximity
                        dist_sl = abs(active_sl - O)
                        dist_tp = abs(active_tp - O)
                        if dist_sl < dist_tp:
                            # SL first
                            if did_enter and i < len(data) - 1:
                                long_exits.iloc[i + 1] = True
                                np_exec_price[i + 1] = round_to_tick(active_sl, ts_tick)
                            else:
                                long_exits.iloc[i] = True
                                np_exec_price[i] = round_to_tick(active_sl, ts_tick)
                        else:
                            # TP first
                            if did_enter and i < len(data) - 1:
                                long_exits.iloc[i + 1] = True
                                np_exec_price[i + 1] = round_to_tick(active_tp, ts_tick)
                            else:
                                long_exits.iloc[i] = True
                                np_exec_price[i] = round_to_tick(active_tp, ts_tick)
                    elif hit_sl:
                        if did_enter and i < len(data) - 1:
                            long_exits.iloc[i + 1] = True
                            np_exec_price[i + 1] = round_to_tick(active_sl, ts_tick)
                        else:
                            long_exits.iloc[i] = True
                            np_exec_price[i] = round_to_tick(active_sl, ts_tick)
                    else:  # hit_tp
                        if did_enter and i < len(data) - 1:
                            long_exits.iloc[i + 1] = True
                            np_exec_price[i + 1] = round_to_tick(active_tp, ts_tick)
                        else:
                            long_exits.iloc[i] = True
                            np_exec_price[i] = round_to_tick(active_tp, ts_tick)
                    
                    active_trade_side = 0
                    trade_closed_this_bar = True
                    
            elif active_trade_side == -1:  # Short position
                hit_sl = H >= active_sl
                hit_tp = L <= active_tp
                
                if hit_sl or hit_tp:
                    if hit_sl and hit_tp:
                        dist_sl = abs(active_sl - O)
                        dist_tp = abs(active_tp - O)
                        if dist_sl < dist_tp:
                            if did_enter and i < len(data) - 1:
                                short_exits.iloc[i + 1] = True
                                np_exec_price[i + 1] = round_to_tick(active_sl, ts_tick)
                            else:
                                short_exits.iloc[i] = True
                                np_exec_price[i] = round_to_tick(active_sl, ts_tick)
                        else:
                            if did_enter and i < len(data) - 1:
                                short_exits.iloc[i + 1] = True
                                np_exec_price[i + 1] = round_to_tick(active_tp, ts_tick)
                            else:
                                short_exits.iloc[i] = True
                                np_exec_price[i] = round_to_tick(active_tp, ts_tick)
                    elif hit_sl:
                        if did_enter and i < len(data) - 1:
                            short_exits.iloc[i + 1] = True
                            np_exec_price[i + 1] = round_to_tick(active_sl, ts_tick)
                        else:
                            short_exits.iloc[i] = True
                            np_exec_price[i] = round_to_tick(active_sl, ts_tick)
                    else:  # hit_tp
                        if did_enter and i < len(data) - 1:
                            short_exits.iloc[i + 1] = True
                            np_exec_price[i + 1] = round_to_tick(active_tp, ts_tick)
                        else:
                            short_exits.iloc[i] = True
                            np_exec_price[i] = round_to_tick(active_tp, ts_tick)
                    
                    active_trade_side = 0
                    trade_closed_this_bar = True
            
            # --- 3. DETECT NEW SIGNAL (BROCHETTE) ---
            can_take_new = True
            if block_new and (active_trade_side != 0 or trade_closed_this_bar or did_enter):
                can_take_new = False
            
            # Clear pending if we already processed it
            if did_enter:
                pending_side = 0
            
            if can_take_new:
                # Skip if market is flat (range filter)
                if not np_is_flat[i]:
                    if np_brochette_bear[i]:
                        # SELL setup
                        pending_side = -1
                        pending_entry_price = C  # Entry at close
                        pending_sl = round_to_tick(H, ts_tick)  # SL at high of signal bar
                        sl_distance = pending_sl - pending_entry_price
                        pending_tp = round_to_tick(pending_entry_price - (rr * sl_distance), ts_tick)
                        
                    elif np_brochette_bull[i]:
                        # BUY setup
                        pending_side = 1
                        pending_entry_price = C  # Entry at close
                        pending_sl = round_to_tick(L, ts_tick)  # SL at low of signal bar
                        sl_distance = pending_entry_price - pending_sl
                        pending_tp = round_to_tick(pending_entry_price + (rr * sl_distance), ts_tick)
        
        # Create output Series
        exec_price = pd.Series(np_exec_price, index=data.index)
        sl_dist_series = pd.Series(np_sl_dist, index=data.index)

        return long_entries, long_exits, short_entries, short_exits, exec_price, sl_dist_series
