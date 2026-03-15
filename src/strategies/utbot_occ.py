from .base import Strategy
import pandas as pd
import numpy as np
import pandas_ta_classic as ta
from typing import Tuple, Dict, Any

class UTBotOCC(Strategy):
    """
    OCC UTBot EMA Strategy.
    Based on Pine Script: 'OCC UTBot EMA'.
    
    Combines Open Close Cross (OCC) using moving averages with UT Bot 
    trailing stops to identify setups, plus an EMA exit strategy.
    
    Features:
    - Higher Timeframe OCC bands (calculates SMMA 8 on grouped HTF candles)
    - UT Bot Trailing Stop with ATR
    - Delayed entries via Setup Confirmation
    - Fixed SL based on recent N candles + tick buffer
    - Partial TP at specific R:R
    - Final TP on EMA cross
    - Force close time option
    """
    
    name = "UTBotOCC"
    manual_exit = True
    
    default_params = {
        # OCC Settings
        "int_res": 7,           # Resolution multiplier for HTF OCC
        
        # UTBot Settings
        "key_value": 1.0,
        "atr_period": 10,
        
        # EMA Final Exit
        "ema_period": 20,
        
        # Risk Management
        "tick_buffer": 2, 
        "partial_rr": 2.0,
        "partial_pct": 0.5,
        "lookback_entry": 3,
        "sl_lookback": 5,
        
        # General Settings
        "tick_size": 0.25,
        "force_close_hour": 22  # Force close trades at this hour (if > 0)
    }
    
    param_ranges = {
        "int_res": [3, 5, 7, 10],
        "key_value": [0.5, 1.0, 1.5, 2.0, 2.5, 3.0],
        "atr_period": [7, 10, 14, 20],
        "ema_period": [10, 20, 50],
        "tick_buffer": [0, 2, 4],
        "partial_rr": [1.5, 2.0, 2.5, 3.0],
        "lookback_entry": [1, 3, 5],
        "sl_lookback": [3, 5, 10]
    }
    
    def generate_signals(
        self, 
        data: pd.DataFrame,
        params: Dict[str, Any] = None
    ) -> Tuple[pd.Series, pd.Series, pd.Series, pd.Series, pd.Series, pd.Series, pd.Series]:
        p = self.get_params(params)
        
        # Hardcoded OCC parameters per user request mapping to defaults in TV
        occ_ma_length = 8
        
        # Data requirements
        min_len = max(occ_ma_length * p['int_res'], p['atr_period'], p['ema_period'], p['sl_lookback']) + 10
        if len(data) < min_len:
            empty = pd.Series(False, index=data.index)
            zeros = pd.Series(0.0, index=data.index)
            nans = pd.Series(np.nan, index=data.index)
            return empty, empty, empty, empty, zeros, nans, nans
            
        real_close = data['Close']
        real_open = data['Open']
        real_high = data['High']
        real_low = data['Low']
        
        # Helper: Time info for force close
        hours = data.index.hour.values if hasattr(data.index, 'hour') else np.zeros(len(data))
        
        # ===========================================
        # 1. Higher Timeframe OCC Calculation
        # ===========================================
        int_res = p['int_res']
        
        # Group by blocks of int_res using integer division on index range
        group_id = np.arange(len(data)) // int_res
        grouped = data.groupby(group_id)
        
        htf_open = grouped['Open'].first()
        htf_close = grouped['Close'].last()
        
        # Calculate SMMA on HTF data
        # SMMA Calculation (similar to RMA in PineScript): RMA[i] = (src[i] + (length - 1) * RMA[i-1]) / length
        htf_occ_open = np.zeros(len(htf_open))
        htf_occ_close = np.zeros(len(htf_close))
        
        if len(htf_open) > occ_ma_length:
            htf_open_vals = htf_open.values
            htf_close_vals = htf_close.values
            
            # Initialize with SMA for the first point
            htf_occ_open[occ_ma_length - 1] = np.mean(htf_open_vals[:occ_ma_length])
            htf_occ_close[occ_ma_length - 1] = np.mean(htf_close_vals[:occ_ma_length])
            
            for i in range(occ_ma_length, len(htf_open)):
                htf_occ_open[i] = (htf_occ_open[i-1] * (occ_ma_length - 1) + htf_open_vals[i]) / occ_ma_length
                htf_occ_close[i] = (htf_occ_close[i-1] * (occ_ma_length - 1) + htf_close_vals[i]) / occ_ma_length
            
            htf_occ_open[:occ_ma_length-1] = htf_occ_open[occ_ma_length-1]
            htf_occ_close[:occ_ma_length-1] = htf_occ_close[occ_ma_length-1]

        htf_occ_open_series = pd.Series(htf_occ_open, index=htf_open.index)
        htf_occ_close_series = pd.Series(htf_occ_close, index=htf_close.index)

        # Expand back to original timeframe (mimicking PineScript's request.security with lookahead_on)
        # Because we need the HTF bar value on each internal bar. 
        # Using transform maps the HTF value back to all rows in that group.
        # This matches the PineScript logic where gap_off/lookahead_on gives the closing value of the HTF bar 
        # across all current smaller timeframe bars.
        occ_open = np.zeros(len(data))
        occ_close = np.zeros(len(data))
        
        for name, group in grouped:
            idx = group.index
            # Get the exact index mapping of the group (it's the first element of idx usually, but we use the 'name' from groupby)
            val_open = htf_occ_open_series.iloc[name]
            val_close = htf_occ_close_series.iloc[name]
            
            occ_open[group_id == name] = val_open
            occ_close[group_id == name] = val_close
            
        occ_upper = np.maximum(occ_open, occ_close)
        occ_lower = np.minimum(occ_open, occ_close)
        
        # ===========================================
        # 2. UT Bot Trailing Stop Calculation
        # ===========================================
        xATR = ta.atr(real_high, real_low, real_close, length=p['atr_period']).bfill()
        nLoss = p['key_value'] * xATR
        
        np_src = real_close.values
        np_nLoss = nLoss.values
        np_trail = np.zeros(len(data))
        
        for i in range(1, len(data)):
            prev_trail = np_trail[i-1]
            curr_src = np_src[i]
            prev_src = np_src[i-1]
            curr_nLoss = np_nLoss[i]
            
            if (curr_src > prev_trail) and (prev_src > prev_trail):
                np_trail[i] = max(prev_trail, curr_src - curr_nLoss)
            elif (curr_src < prev_trail) and (prev_src < prev_trail):
                np_trail[i] = min(prev_trail, curr_src + curr_nLoss)
            elif curr_src > prev_trail:
                np_trail[i] = curr_src - curr_nLoss
            else:
                np_trail[i] = curr_src + curr_nLoss
                
        xATRTrailingStop = np_trail
        
        # ===========================================
        # 3. UT Bot Signals (Fixed Crossover Logic)
        # ===========================================
        ut_buy = np.zeros(len(data), dtype=bool)
        ut_sell = np.zeros(len(data), dtype=bool)
        
        for i in range(1, len(data)):
            curr_src = np_src[i]
            prev_src = np_src[i-1]
            curr_trail = xATRTrailingStop[i]
            prev_trail = xATRTrailingStop[i-1]
            
            # Crossover strict implementation:
            # src[i-1] <= trail[i-1] AND src[i] > trail[i]
            ut_above = (prev_src <= prev_trail) and (curr_src > curr_trail)
            ut_below = (prev_src >= prev_trail) and (curr_src < curr_trail)
            
            # utBuy = utSrc > xATRTrailingStop and utAbove 
            # (since utAbove already requires curr_src > curr_trail, the first condition is redundant but we keep it for strictness)
            ut_buy[i] = (curr_src > curr_trail) and ut_above
            ut_sell[i] = (curr_src < curr_trail) and ut_below
            
        # ===========================================
        # 4. Global Lookbacks & EMA
        # ===========================================
        ema_exit = ta.ema(real_close, length=p['ema_period']).bfill().values
        
        # 5-candle highest/lowest for stop loss calculation
        sl_lookback = p['sl_lookback']
        lowest_five_low = real_low.rolling(window=sl_lookback, min_periods=1).min().values
        highest_five_high = real_high.rolling(window=sl_lookback, min_periods=1).max().values
        
        tick_sz = p['tick_size'] if p['tick_size'] > 0 else 0.25
        def round_to_tick(price: float) -> float:
            if np.isnan(price): return price
            return round(price / tick_sz) * tick_sz

        tick_buffer_val = p['tick_buffer'] * tick_sz
        
        # ===========================================
        # 5. Position Management State Machine
        # ===========================================
        n = len(data)
        long_entries = pd.Series(False, index=data.index)
        long_exits = pd.Series(False, index=data.index)
        short_entries = pd.Series(False, index=data.index)
        short_exits = pd.Series(False, index=data.index)
        exec_prices = real_close.copy()
        sl_dists = pd.Series(np.nan, index=data.index)
        exit_ratios = pd.Series(1.0, index=data.index)
        
        # State variables
        in_pos = False
        pos_side = 0           # 1 for Long, -1 for Short
        entry_price = np.nan
        stop_price = np.nan
        tp_price = np.nan
        partial_taken = False
        last_action_bar = -1
        
        setup_pending = False
        setup_side = 0
        setup_bar = -1
        setup_bars_left = 0
        setup_stop_long = np.nan
        setup_stop_short = np.nan
        
        np_high = real_high.values
        np_low = real_low.values
        np_close = real_close.values
        
        for i in range(1, n):
            # 0. Force Close Time Check
            force_close = p['force_close_hour'] > 0 and hours[i] >= p['force_close_hour']
            
            if in_pos and force_close and i > last_action_bar:
                # Close the position completely on this bar.
                if pos_side == 1:
                    long_exits.iloc[i] = True
                    exec_prices.iloc[i] = np_close[i]
                else:
                    short_exits.iloc[i] = True
                    exec_prices.iloc[i] = np_close[i]
                    
                exit_ratios.iloc[i] = 1.0
                
                # Reset State
                in_pos = False
                pos_side = 0
                partial_taken = False
                last_action_bar = i
                continue  # Stop evaluating exits/entries for this bar
            
            # --- SETUP DETECTION ---
            # Long Setup : UT Bot buy + bougie TOUCHE la bande OCC (low <= occUpper) + clôture AU-DESSUS (close > occUpper)
            long_setup_signal = ut_buy[i] and (np_low[i] <= occ_upper[i]) and (np_close[i] > occ_upper[i])
            
            # Short Setup : UT Bot sell + bougie TOUCHE la bande OCC (high >= occLower) + clôture EN-DESSOUS (close < occLower)
            short_setup_signal = ut_sell[i] and (np_high[i] >= occ_lower[i]) and (np_close[i] < occ_lower[i])
            
            # Note: PineScript has inBlackout and forceClose filters for setups
            blackout = False # Ignore blackout for standard backtest unless specified
            
            if long_setup_signal and not in_pos and not blackout and not force_close:
                setup_pending = True
                setup_side = 1
                setup_bar = i
                setup_bars_left = p['lookback_entry']
                setup_stop_long = lowest_five_low[i] - tick_buffer_val
                
            if short_setup_signal and not in_pos and not blackout and not force_close:
                setup_pending = True
                setup_side = -1
                setup_bar = i
                setup_bars_left = p['lookback_entry']
                setup_stop_short = highest_five_high[i] + tick_buffer_val
                
            # --- CONFIRMATION ENTRÉE ---
            long_entry_confirm = False
            short_entry_confirm = False
            
            # The original Pine says: bar_index > setupBar. 
            # That implies we evaluate confirming entry ONLY starting from the bar AFTER the setup bar.
            if setup_pending and setup_side == 1 and i > setup_bar and np_low[i] <= occ_upper[i]:
                long_entry_confirm = True
                
            if setup_pending and setup_side == -1 and i > setup_bar and np_high[i] >= occ_lower[i]:
                short_entry_confirm = True
                
            # --- TIMER DECREMENT ---
            if setup_pending and i > setup_bar and not long_entry_confirm and not short_entry_confirm:
                setup_bars_left -= 1
                if setup_bars_left <= 0:
                    setup_pending = False
                    setup_side = 0
                    setup_bar = -1
                    setup_bars_left = 0
                    setup_stop_long = np.nan
                    setup_stop_short = np.nan
                    
            # --- SORTIES (EXITS) ---
            # Exit evaluation happens only if in_pos and i > last_action_bar (same candle safety)
            if in_pos and i > last_action_bar:
                hit_sl_long = (pos_side == 1) and (np_low[i] <= stop_price)
                hit_sl_short = (pos_side == -1) and (np_high[i] >= stop_price)
                
                hit_tp_long = (pos_side == 1) and not partial_taken and (np_high[i] >= tp_price)
                hit_tp_short = (pos_side == -1) and not partial_taken and (np_low[i] <= tp_price)
                
                hit_final_long = (pos_side == 1) and partial_taken and (np_close[i] < ema_exit[i])
                hit_final_short = (pos_side == -1) and partial_taken and (np_close[i] > ema_exit[i])
                
                # Priority: SL > TP Partiel > TP Final
                if hit_sl_long:
                    long_exits.iloc[i] = True
                    exec_prices.iloc[i] = round_to_tick(stop_price)
                    exit_ratios.iloc[i] = 1.0
                    
                    in_pos = False
                    pos_side = 0
                    partial_taken = False
                    last_action_bar = i
                    continue
                    
                elif hit_sl_short:
                    short_exits.iloc[i] = True
                    exec_prices.iloc[i] = round_to_tick(stop_price)
                    exit_ratios.iloc[i] = 1.0
                    
                    in_pos = False
                    pos_side = 0
                    partial_taken = False
                    last_action_bar = i
                    continue
                    
                # We do not `continue` after partials because we could theoretically hit final EMA or SL next bar (but Pine limits 1 action/bar usually)
                elif hit_tp_long:
                    partial_taken = True
                    # In backtesting framework, partials are tricky.
                    # We log the exit and reduce position size. Since our Strategy framework handles ratio:
                    long_exits.iloc[i] = True
                    exec_prices.iloc[i] = round_to_tick(tp_price)
                    exit_ratios.iloc[i] = p['partial_pct']
                    
                    # Move SL to BE
                    stop_price = entry_price
                    last_action_bar = i
                    
                elif hit_tp_short:
                    partial_taken = True
                    short_exits.iloc[i] = True
                    exec_prices.iloc[i] = round_to_tick(tp_price)
                    exit_ratios.iloc[i] = p['partial_pct']
                    
                    # Move SL to BE
                    stop_price = entry_price
                    last_action_bar = i
                    
                elif hit_final_long:
                    long_exits.iloc[i] = True
                    exec_prices.iloc[i] = round_to_tick(np_close[i])
                    exit_ratios.iloc[i] = 1.0
                    
                    in_pos = False
                    pos_side = 0
                    partial_taken = False
                    last_action_bar = i
                    continue
                    
                elif hit_final_short:
                    short_exits.iloc[i] = True
                    exec_prices.iloc[i] = round_to_tick(np_close[i])
                    exit_ratios.iloc[i] = 1.0
                    
                    in_pos = False
                    pos_side = 0
                    partial_taken = False
                    last_action_bar = i
                    continue

            # --- ENTRÉES (ENTRIES) ---
            if not in_pos and long_entry_confirm and i > last_action_bar and not blackout and not force_close:
                # execute long
                in_pos = True
                pos_side = 1
                
                entry_price_raw = occ_upper[i]
                entry_price = round_to_tick(entry_price_raw)
                stop_price = round_to_tick(setup_stop_long)
                
                risk = entry_price - (stop_price if not np.isnan(stop_price) else entry_price)
                tp_price_raw = entry_price + (risk * p['partial_rr'])
                tp_price = round_to_tick(tp_price_raw)
                
                partial_taken = False
                last_action_bar = i
                
                setup_pending = False
                setup_side = 0
                setup_bar = -1
                setup_bars_left = 0
                setup_stop_long = np.nan
                
                long_entries.iloc[i] = True
                exec_prices.iloc[i] = entry_price
                sl_dists.iloc[i] = entry_price - stop_price
                
            elif not in_pos and short_entry_confirm and i > last_action_bar and not blackout and not force_close:
                # execute short
                in_pos = True
                pos_side = -1
                
                entry_price_raw = occ_lower[i]
                entry_price = round_to_tick(entry_price_raw)
                stop_price = round_to_tick(setup_stop_short)
                
                risk = (stop_price if not np.isnan(stop_price) else entry_price) - entry_price
                tp_price_raw = entry_price - (risk * p['partial_rr'])
                tp_price = round_to_tick(tp_price_raw)
                
                partial_taken = False
                last_action_bar = i
                
                setup_pending = False
                setup_side = 0
                setup_bar = -1
                setup_bars_left = 0
                setup_stop_short = np.nan
                
                short_entries.iloc[i] = True
                exec_prices.iloc[i] = entry_price
                sl_dists.iloc[i] = stop_price - entry_price

        return long_entries, long_exits, short_entries, short_exits, exec_prices, sl_dists, exit_ratios
