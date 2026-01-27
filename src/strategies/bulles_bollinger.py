from .base import Strategy
import pandas as pd
import numpy as np
import pandas_ta_classic as ta
from typing import Tuple, Dict, Any

class BullesBollinger(Strategy):
    """
    Stratégie Bulles de Bollinger - Classiques
    Translates the PineScript 'Bulles de Bollinger - Classiques' strategy.
    
    Refined V2:
    - Removed unused 'stop_loss_lookback' and 'tp_partial_ratio'.
    - Removed 'Safety SL' logic to strictly match Pine.
    - Enforced strict mutual exclusivity between TP1 checks and TP2 checks in the same bar.
    """
    
    name = "BullesBollinger"
    manual_exit = True
    
    default_params = {
        # Bollinger Bands Settings
        "bb_length": 20,
        "bb_mult": 2.0,
        
        # Filters
        "filter_bulldozer": True,
        
        # Position Management
        # "stop_loss_lookback": Unused in this strategy (SL is based on specific candle High/Low)
        # "tp_partial_ratio": Unused (TP is dynamic based on Basis)
        
        "tp_partial_pct": 0.5,   # Close 50% at TP1
        "tick_size": 0.25
    }

    def generate_signals(
        self, 
        data: pd.DataFrame, 
        params: Dict[str, Any] = None
    ) -> Tuple[pd.Series, pd.Series, pd.Series, pd.Series, pd.Series, pd.Series, pd.Series]:
        p = self.get_params(params)
        
        close_real = data['Close']
        open_real = data['Open']
        high_real = data['High']
        low_real = data['Low']
        
        # 1. Bollinger Bands Calculation
        bb_length = p['bb_length']
        bb_mult = p['bb_mult']
        
        basis = ta.sma(close_real, length=bb_length)
        # Switch to Population Standard Deviation (ddof=0) to match TradingView/Pine
        stdev = close_real.rolling(window=bb_length, min_periods=bb_length).std(ddof=0)
        dev = bb_mult * stdev
        upper = basis + dev
        lower = basis - dev
        
        # 2. Logic Detection (Vectorized)
        
        # Barre A - Setup (Previous Candle [1])
        # Shifted to align with "Current" candle being 0, acts on [1]
        
        prev_open = open_real.shift(1)
        prev_close = close_real.shift(1)
        prev_high = high_real.shift(1)
        prev_low = low_real.shift(1)
        
        prev_lower = lower.shift(1)
        prev_upper = upper.shift(1)
        
        barre_a_buy = (prev_open < prev_lower) & (prev_close < prev_lower) & (prev_high >= prev_lower)
        barre_a_sell = (prev_open > prev_upper) & (prev_close > prev_upper) & (prev_low <= prev_upper)
        
        # Trigger Conditions (Current Candle [0])
        
        is_green = close_real > open_real
        is_red = close_real < open_real
        
        trigger_buy = barre_a_buy & (close_real >= lower) & (close_real <= upper) & is_green
        trigger_sell = barre_a_sell & (close_real >= lower) & (close_real <= upper) & is_red
        
        # 3. Bulldozer Filter
        if p['filter_bulldozer']:
            open_2 = open_real.shift(2)
            close_2 = close_real.shift(2)
            high_2 = high_real.shift(2)
            low_2 = low_real.shift(2)
            lower_2 = lower.shift(2)
            upper_2 = upper.shift(2)
            
            prev_was_bubble_buy = ((open_2 < lower_2) & (close_2 < lower_2)) | (high_2 < lower_2)
            prev_was_bubble_sell = ((open_2 > upper_2) & (close_2 > upper_2)) | (low_2 > upper_2)
            
            signal_buy = trigger_buy & (~prev_was_bubble_buy)
            signal_sell = trigger_sell & (~prev_was_bubble_sell)
        else:
            signal_buy = trigger_buy
            signal_sell = trigger_sell
            
        # 4. Position Management Loop
        
        long_entries = pd.Series(False, index=data.index)
        long_exits = pd.Series(False, index=data.index)
        short_entries = pd.Series(False, index=data.index)
        short_exits = pd.Series(False, index=data.index)
        exec_prices = close_real.copy() 
        sl_dists = pd.Series(np.nan, index=data.index)
        exit_ratios = pd.Series(1.0, index=data.index)
        
        # Numpy arrays
        np_close = close_real.values
        np_high = high_real.values
        np_low = low_real.values
        
        np_buy = signal_buy.values
        np_sell = signal_sell.values
        
        np_basis = basis.values
        np_upper = upper.values
        np_lower = lower.values
        
        # Params
        tp_pct = p['tp_partial_pct']
        tick_sz = p['tick_size']
        
        # State Variables
        in_pos = False
        pos_side = 0 # 1 Long, -1 Short
        entry_price = 0.0
        current_sl = 0.0
        
        tp1_hit = False
        entry_idx = -1
        
        def round_to_tick(price, tick_size):
             return round(price / tick_size) * tick_size
             
        # Start Loop
        for i in range(2, len(data)):
            
            # --- Check Exits ---
            if in_pos and i != entry_idx:
                
                # Dynamic Levels for this bar
                idx_high = np_high[i]
                idx_low = np_low[i]
                # idx_close = np_close[i] # Unused directly
                
                curr_basis = np_basis[i]
                curr_upper = np_upper[i]
                curr_lower = np_lower[i]
                    
                if pos_side == 1: # LONG
                    # 1. STOP LOSS Check (Or BE if moved)
                    # "if not tp1Hit... if ... low <= activeSL"
                    if idx_low <= current_sl:
                        long_exits.iloc[i] = True
                        exec_prices.iloc[i] = current_sl
                        in_pos = False
                        pos_side = 0
                        continue
                        
                    # 2. TP1 Logic (Pine: if not tp1Hit)
                    if not tp1_hit:
                        # Check TP1 (Basis)
                        if idx_high >= curr_basis:
                            tp1_hit = True
                            current_sl = entry_price # Move SL to BE
                            
                            # Partial Exit Signal
                            long_exits.iloc[i] = True
                            exec_prices.iloc[i] = curr_basis
                            exit_ratios.iloc[i] = tp_pct
                            # IMPORTANT: In Pine, if we enter this block (tp1 hit), 
                            # we DO NOT execute the 'else' block (TP2 check) in the same script execution.
                            # So we continue to next bar.
                            continue
                            
                    # 3. TP2 Logic (Pine: else...) via 'elif' logic implied by 'continue' above
                    else: # tp1_hit is True (from previous bars)
                        # Check TP2 (Upper Band)
                        if idx_high >= curr_upper:
                            long_exits.iloc[i] = True
                            exec_prices.iloc[i] = curr_upper
                            in_pos = False
                            pos_side = 0
                            continue
                            
                elif pos_side == -1: # SHORT
                    # 1. STOP LOSS Check
                    if idx_high >= current_sl:
                        short_exits.iloc[i] = True
                        exec_prices.iloc[i] = current_sl
                        in_pos = False
                        pos_side = 0
                        continue
                        
                    # 2. TP1 Logic
                    if not tp1_hit:
                        if idx_low <= curr_basis:
                            tp1_hit = True
                            current_sl = entry_price # Move SL to BE
                            
                            short_exits.iloc[i] = True
                            exec_prices.iloc[i] = curr_basis
                            exit_ratios.iloc[i] = tp_pct
                            continue
                            
                    # 3. TP2 Logic
                    else:
                        if idx_low <= curr_lower:
                            short_exits.iloc[i] = True
                            exec_prices.iloc[i] = curr_lower
                            in_pos = False
                            pos_side = 0
                            continue

            # --- Check Entries ---
            if not in_pos:
                
                if np_buy[i]:
                    entry_p = round_to_tick(np_close[i], tick_sz)
                    
                    long_entries.iloc[i] = True
                    exec_prices.iloc[i] = entry_p
                    in_pos = True
                    pos_side = 1
                    entry_idx = i
                    entry_price = entry_p
                    tp1_hit = False
                    
                    # SL Setup: Low of Previous Candle [i-1] (Barre A)
                    raw_sl = np_low[i-1]
                    initial_sl = round_to_tick(raw_sl, tick_sz)
                    
                    # NOTE: Removed Safety Check (initial_sl >= entry_price) to match Pine strict logic.
                        
                    current_sl = initial_sl
                    risk = entry_price - current_sl
                    sl_dists.iloc[i] = risk
                    
                elif np_sell[i]:
                    entry_p = round_to_tick(np_close[i], tick_sz)
                    
                    short_entries.iloc[i] = True
                    exec_prices.iloc[i] = entry_p
                    in_pos = True
                    pos_side = -1
                    entry_idx = i
                    entry_price = entry_p
                    tp1_hit = False
                    
                    # SL Setup: High of Previous Candle [i-1] (Barre A)
                    raw_sl = np_high[i-1]
                    initial_sl = round_to_tick(raw_sl, tick_sz)
                    
                    # NOTE: Removed Safety Check
                         
                    current_sl = initial_sl
                    risk = current_sl - entry_price
                    sl_dists.iloc[i] = risk
                    
        return long_entries, long_exits, short_entries, short_exits, exec_prices, sl_dists, exit_ratios
