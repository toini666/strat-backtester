from .base import Strategy
import pandas as pd
import numpy as np
import pandas_ta_classic as ta
from typing import Tuple, Dict, Any

class UTBotHeikin(Strategy):
    """
    UTBot Strategy with Heikin Ashi option and Ribbons/RSI filters.
    Based on Pine Script implementation: 'UTBotRibbonHeikin'.
    """
    
    name = "UTBotHeikin"
    manual_exit = True
    
    default_params = {
        # UTBot Settings
        "key_value": 1,
        "atr_period": 10,
        "use_heikin_ashi": True,
        
        # EMA Ribbon Settings (Filters)
        "ribbon_enabled": True,
        "ribbon_length": 20,
        "ribbon_step": 5,
        "ribbon_count": 8,
        
        # RSI Settings (Filter)
        "rsi_enabled": True,
        "rsi_length": 14,
        "rsi_lookback": 5,
        "rsi_long_level": 40,  # <= for Long
        "rsi_short_level": 60, # >= for Short
        
        # EMA200 Settings (Filter)
        "ema200_filter_enabled": True,
        "ema200_length": 200,
        "ema200_lookback_check": True, # Check if all closes in lookback are above/below
        
        # Position Management
        "stop_loss_lookback": 5,
        "tp_partial_ratio": 2.0,
        "tp_partial_pct": 0.5, # Percentage to close on partial TP (0.0 - 1.0)
        "tick_size": 0.25
    }

    def generate_signals(
        self, 
        data: pd.DataFrame, 
        params: Dict[str, Any] = None
    ) -> Tuple[pd.Series, pd.Series, pd.Series, pd.Series, pd.Series, pd.Series, pd.Series]:
        p = self.get_params(params)
        
        # Ensure we have enough data
        if len(data) < p['ema200_length']:
            empty = pd.Series(False, index=data.index)
            zeros = pd.Series(0.0, index=data.index)
            nans = pd.Series(np.nan, index=data.index)
            return empty, empty, empty, empty, zeros, nans, nans

        close_real = data['Close']
        open_real = data['Open']
        high_real = data['High']
        low_real = data['Low']
        
        # 1. Heikin Ashi Calculation
        # Always calculate HA to support the toggle fully
        
        ha_close = (open_real + high_real + low_real + close_real) / 4
        
        # HA Open requires iteration
        # Standard calculation:
        ha_open = pd.Series(0.0, index=data.index)
        ha_open.iloc[0] = open_real.iloc[0] # Initialize first with actual open
        
        np_ha_open = np.zeros(len(data))
        np_ha_open[0] = open_real.values[0]
        np_ha_close = ha_close.values
        
        for i in range(1, len(data)):
            np_ha_open[i] = (np_ha_open[i-1] + np_ha_close[i-1]) / 2
            
        ha_open[:] = np_ha_open
        
        # HA High/Low
        # Valid HA High is max of High, HA Open, HA Close
        ha_high = pd.DataFrame({'a': high_real, 'b': ha_open, 'c': ha_close}).max(axis=1)
        ha_low = pd.DataFrame({'a': low_real, 'b': ha_open, 'c': ha_close}).min(axis=1)

        # 2. Select Candle Source for Strategy Logic
        if p['use_heikin_ashi']:
            # Use HA for EVERYTHING to match TradingView HA Chart behavior
            calc_open = ha_open
            calc_high = ha_high
            calc_low = ha_low
            calc_close = ha_close
        else:
            # Use Real candles
            calc_open = open_real
            calc_high = high_real
            calc_low = low_real
            calc_close = close_real

        src = calc_close.copy()

        # 2. UTBot Trailing Stop Logic
        # xATR = ta.atr(atrPeriod)
        xATR = ta.atr(calc_high, calc_low, calc_close, length=p['atr_period'])
        nLoss = p['key_value'] * xATR
        
        # Recursive Trailing Stop calculation
        # xATRTrailingStop := ...
        # Can use numpy loop
        np_src = src.values
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
            elif (curr_src > prev_trail):
                np_trail[i] = curr_src - curr_nLoss
            else:
                np_trail[i] = curr_src + curr_nLoss
                
        xATRTrailingStop = pd.Series(np_trail, index=data.index)
        
        # Buy/Sell Signals based on Trailing Stop Crossover
        # ema_signal = ta.ema(src, 1) -> Effectively just src
        # above = ta.crossover(ema_signal, xATRTrailingStop) -> src crosses over trail
        # below = ta.crossover(xATRTrailingStop, ema_signal) -> trail crosses over src
        
        # In Pine: buy = src > xATRTrailingStop and above
        # Actually logic is state-based "pos".
        # pos := src[1] < nz(xATRTrailingStop[1], 0) and src > nz(xATRTrailingStop[1], 0) ? 1 : ...
        
        # Let's Vectorize Position State
        # -1 = Short Env, 1 = Long Env
        # Buy Signal when flipping from -1 to 1
        
        # Shifted comparison for crossover
        prev_src = src.shift(1)
        prev_trail = xATRTrailingStop.shift(1)
        
        buy_signal_raw = (src > xATRTrailingStop) & (prev_src < prev_trail)
        sell_signal_raw = (src < xATRTrailingStop) & (prev_src > prev_trail)
        
        # 3. Filters (Using Selected Candle Source)
        
        # A. Ribbon Filter
        # emaFast > emaSlow (Green) or < (Red)
        if p['ribbon_enabled']:
            ema_fast = ta.ema(calc_close, length=p['ribbon_length'])
            # Calc Slow index: length + (step * (count - 1))
            slow_len = p['ribbon_length'] + (p['ribbon_step'] * (p['ribbon_count'] - 1))
            ema_slow = ta.ema(calc_close, length=slow_len)
            
            ribbon_green = ema_fast > ema_slow
            ribbon_red = ema_fast < ema_slow
        else:
            ribbon_green = pd.Series(True, index=data.index)
            ribbon_red = pd.Series(True, index=data.index)
            
        # B. EMA 200 Filter
        if p['ema200_filter_enabled']:
            ema200 = ta.ema(calc_close, length=p['ema200_length'])
            
            # Simple check
            price_above_ema = calc_close > ema200
            price_below_ema = calc_close < ema200
            
            # Lookback check logic (Pine: allClosesAboveEma200 in last X bars)
            # "For LONG: reject if any close below EMA200 in lookback" -> All must be above
            if p['ema200_lookback_check']:
                lookback = p['rsi_lookback'] # Pine uses RSI lookback for this loop? Yes: "for i = 0 to rsiLookback - 1"
                # Using rolling min to check if all > ema
                # We need to check if (Close - EMA200) > 0 for all window
                # Alternatively: Rolling apply.
                # Optimized: We can use comparison series
                is_above = (calc_close > ema200).astype(int)
                is_below = (calc_close < ema200).astype(int)
                
                # If sum of last N days == N, then all were true
                all_closes_above = is_above.rolling(window=lookback).sum() == lookback
                all_closes_below = is_below.rolling(window=lookback).sum() == lookback
                
                final_ema_long_cond = all_closes_above
                final_ema_short_cond = all_closes_below
            else:
                final_ema_long_cond = price_above_ema
                final_ema_short_cond = price_below_ema
        else:
            final_ema_long_cond = pd.Series(True, index=data.index)
            final_ema_short_cond = pd.Series(True, index=data.index)
            
        # C. RSI Filter
        if p['rsi_enabled']:
            rsi = ta.rsi(calc_close, length=p['rsi_length'])
            # Pine: rsiWasLow = ta.lowest(rsi, rsiLookback) <= rsiLongLevel
            rsi_lowest = rsi.rolling(window=p['rsi_lookback']).min()
            rsi_highest = rsi.rolling(window=p['rsi_lookback']).max()
            
            rsi_was_low = rsi_lowest <= p['rsi_long_level']
            rsi_was_high = rsi_highest >= p['rsi_short_level']
        else:
            rsi_was_low = pd.Series(True, index=data.index)
            rsi_was_high = pd.Series(True, index=data.index)
            
        # Combine Filters
        filtered_buy = buy_signal_raw & rsi_was_low & final_ema_long_cond & ribbon_green
        filtered_sell = sell_signal_raw & rsi_was_high & final_ema_short_cond & ribbon_red
        
        # 4. Position Management Loop (Using Selected Candle Source for Levels)
        long_entries = pd.Series(False, index=data.index)
        long_exits = pd.Series(False, index=data.index)
        short_entries = pd.Series(False, index=data.index)
        short_exits = pd.Series(False, index=data.index)
        exec_prices = calc_close.copy() # Use logic close (Real or HA) for recording
        sl_dists = pd.Series(np.nan, index=data.index)
        exit_ratios = pd.Series(1.0, index=data.index) # Default 100% exit
        
        # Arrays for loop
        np_calc_close = calc_close.values
        np_calc_high = calc_high.values
        np_calc_low = calc_low.values
        np_buy = filtered_buy.values
        np_sell = filtered_sell.values
        np_atr_trail = xATRTrailingStop.values
        
        sl_lookback = p['stop_loss_lookback']
        tp_ratio = p['tp_partial_ratio']
        tp_pct = p['tp_partial_pct']
        
        in_pos = False
        pos_side = 0
        entry_price = 0.0
        current_sl = 0.0
        partial_tp_price = 0.0
        partial_taken = False
        entry_idx = -1
        
        # Helper for rounding
        def round_to_tick(price, tick_size):
             return round(price / tick_size) * tick_size

        for i in range(sl_lookback, len(data)):
            
            if in_pos:
                # Use Calc High/Low/Close (HA or Real) to check exits
                # matching "Chart Visualization"
                idx_low = np_calc_low[i]
                idx_high = np_calc_high[i]
                idx_close = np_calc_close[i]
                
                if i != entry_idx:
                    if pos_side == 1: # LONG
                        if idx_low <= current_sl:
                            long_exits.iloc[i] = True
                            exec_prices.iloc[i] = current_sl
                            in_pos = False
                            pos_side = 0
                            continue
                        
                        if not partial_taken and idx_high >= partial_tp_price:
                            partial_taken = True
                            current_sl = entry_price 
                            
                            # Partial Exit Signal
                            long_exits.iloc[i] = True
                            exec_prices.iloc[i] = partial_tp_price # Execution at Target Level
                            exit_ratios.iloc[i] = tp_pct
                            # Note: in_pos REMAINS True because we still hold position
                            
                        trail_cross = idx_close < np_atr_trail[i]
                        if partial_taken and trail_cross:
                            long_exits.iloc[i] = True
                            exec_prices.iloc[i] = round_to_tick(idx_close, tick_sz)
                            in_pos = False
                            pos_side = 0
                            continue
                            
                    elif pos_side == -1: # SHORT
                        if idx_high >= current_sl:
                            short_exits.iloc[i] = True
                            exec_prices.iloc[i] = current_sl
                            in_pos = False
                            pos_side = 0
                            continue
                            
                        if not partial_taken and idx_low <= partial_tp_price:
                            partial_taken = True
                            current_sl = entry_price 
                            
                            # Partial Exit Signal
                            short_exits.iloc[i] = True
                            exec_prices.iloc[i] = partial_tp_price
                            exit_ratios.iloc[i] = tp_pct
                            # Note: in_pos REMAINS True
                            
                        trail_cross = idx_close > np_atr_trail[i]
                        if partial_taken and trail_cross:
                            short_exits.iloc[i] = True
                            exec_prices.iloc[i] = round_to_tick(idx_close, tick_sz)
                            in_pos = False
                            pos_side = 0
                            continue

            if not in_pos: 
                tick_sz = p['tick_size']

                if np_buy[i]:
                    entry_p = round_to_tick(np_calc_close[i], tick_sz)
                    
                    long_entries.iloc[i] = True
                    exec_prices.iloc[i] = entry_p
                    in_pos = True
                    pos_side = 1
                    entry_idx = i
                    entry_price = entry_p
                    partial_taken = False
                    
                    window_lows = np_calc_low[i-sl_lookback+1 : i+1]
                    raw_sl = np.min(window_lows)
                    initial_sl = round_to_tick(raw_sl, tick_sz)
                    
                    if initial_sl >= entry_price:
                        initial_sl = entry_price - tick_sz * 10
                        
                    current_sl = initial_sl
                    risk = entry_price - current_sl
                    partial_tp_price = round_to_tick(entry_price + (risk * tp_ratio), tick_sz)
                    sl_dists.iloc[i] = risk

                elif np_sell[i]:
                    entry_p = round_to_tick(np_calc_close[i], tick_sz)
                    
                    short_entries.iloc[i] = True
                    exec_prices.iloc[i] = entry_p
                    in_pos = True
                    pos_side = -1
                    entry_idx = i
                    entry_price = entry_p
                    partial_taken = False
                    
                    window_highs = np_calc_high[i-sl_lookback+1 : i+1]
                    raw_sl = np.max(window_highs)
                    initial_sl = round_to_tick(raw_sl, tick_sz)
                    
                    if initial_sl <= entry_price:
                        initial_sl = entry_price + tick_sz * 10
                        
                    current_sl = initial_sl
                    risk = current_sl - entry_price
                    partial_tp_price = round_to_tick(entry_price - (risk * tp_ratio), tick_sz)
                    sl_dists.iloc[i] = risk
                    
        return long_entries, long_exits, short_entries, short_exits, exec_prices, sl_dists, exit_ratios
        
        # Lookback params
        sl_lookback = p['stop_loss_lookback']
        tp_ratio = p['tp_partial_ratio']
        
        # State
        in_pos = False
        pos_side = 0 # 1 long, -1 short
        entry_price = 0.0
        current_sl = 0.0
        partial_tp_price = 0.0
        partial_taken = False
        entry_idx = -1
        
        # Helper for rounding
        def round_to_tick(price, tick_size):
             return round(price / tick_size) * tick_size

        # We start loop
        for i in range(sl_lookback, len(data)):
            
            # --- Check Exits First ---
            if in_pos:
                # 1. Check SL
                # 2. Check Partial TP
                # 3. Check Final Exit (Trailing Stop Reversal)
                
                idx_low = np_low[i]
                idx_high = np_high[i]
                idx_close = np_close[i]
                idx_open = data['Open'].values[i] # Use actual open for execution if needed? No, usually Close.
                
                # Filter: Don't exit on entry bar (Pine: bar_index != entryBar)
                if i != entry_idx:
                    
                    if pos_side == 1: # LONG
                        # Check SL
                        if idx_low <= current_sl:
                            long_exits.iloc[i] = True
                            exec_prices.iloc[i] = current_sl
                            in_pos = False
                            pos_side = 0
                            continue # Trade closed
                        
                        # Check Partial TP
                        if not partial_taken and idx_high >= partial_tp_price:
                            partial_taken = True
                            current_sl = entry_price # Move to BE
                            # Note: In Pine, if partial hit, we stay in position but move SL.
                            # We do NOT exit. 
                            
                        # Check Final Exit (reversal of trend)
                        # Pine Logic: finalExitLong = ... partialTaken and close < xATRTrailingStop
                        # It specifically requires partialTaken to be TRUE to trigger this exit?
                        # "stopHitLong = ... low <= stopLoss and not partialTaken"
                        # "abeHitLong = ... low <= stopLoss and partialTaken"
                        # "finalExitLong = ... partialTaken and close < xATRTrailingStop"
                        # IMPLICATION: If Close < Trail BUT Partial NOT taken, do we exit?
                        # Pine code: `if finalExitLong ... alert("CLOSE")`. 
                        # This implies if partial NOT taken, we ignore trailing stop crossover!
                        # We only exit via Initial Stop Loss.
                        # Only AFTER partial is taken do we respect the Trailing Stop Reversal.
                        
                        trail_cross = idx_close < np_atr_trail[i]
                        
                        if partial_taken and trail_cross:
                            long_exits.iloc[i] = True
                            exec_prices.iloc[i] = idx_close
                            in_pos = False
                            pos_side = 0
                            continue
                            
                    elif pos_side == -1: # SHORT
                        # Check SL
                        if idx_high >= current_sl:
                            short_exits.iloc[i] = True
                            exec_prices.iloc[i] = current_sl
                            in_pos = False
                            pos_side = 0
                            continue
                            
                        # Check Partial TP
                        if not partial_taken and idx_low <= partial_tp_price:
                            partial_taken = True
                            current_sl = entry_price # BE
                            
                        # Check Final Exit
                        trail_cross = idx_close > np_atr_trail[i]
                        
                        if partial_taken and trail_cross:
                            short_exits.iloc[i] = True
                            exec_prices.iloc[i] = idx_close
                            in_pos = False
                            pos_side = 0
                            continue

            # --- Check Entries ---
            if not in_pos: 
                # Strict Filter Check from Pine:
                # filteredBuySignal = buy and rsiWasLow and priceAboveEma200 and ribbonGreen and (ema200Filter ? allClosesAboveEma200 : true)
                
                # Note on User Comment: "EMA Ribbon must be above EMA"
                # While not explicitly in the Pine provided, adding `ema_fast > ema200` ensures strictly stronger trend.
                # However, strictly following the file provided:
                # `ribbonGreen` (Fast>Slow) + `allClosesAboveEma200` (Price > EMA200) usually aligns.
                # We will stick to the exact boolean logic computed in step 3.
                
                tick_sz = p['tick_size']

                if np_buy[i]:
                    entry_p = round_to_tick(np_close[i], tick_sz)
                    
                    long_entries.iloc[i] = True
                    exec_prices.iloc[i] = entry_p
                    in_pos = True
                    pos_side = 1
                    entry_idx = i
                    entry_price = entry_p
                    partial_taken = False
                    
                    # Calc SL / TP
                    # Pine: lowest(low, stopLossLookback)
                    # Window: [i-lookback+1 ... i]
                    window_lows = np_low[i-sl_lookback+1 : i+1]
                    raw_sl = np.min(window_lows)
                    initial_sl = round_to_tick(raw_sl, tick_sz)
                    
                    # Safety
                    if initial_sl >= entry_price:
                        initial_sl = entry_price - tick_sz * 10
                        
                    current_sl = initial_sl
                    risk = entry_price - current_sl
                    partial_tp_price = round_to_tick(entry_price + (risk * tp_ratio), tick_sz)
                    
                    # Save metrics
                    sl_dists.iloc[i] = risk

                elif np_sell[i]:
                    entry_p = round_to_tick(np_close[i], tick_sz)
                    
                    short_entries.iloc[i] = True
                    exec_prices.iloc[i] = entry_p
                    in_pos = True
                    pos_side = -1
                    entry_idx = i
                    entry_price = entry_p
                    partial_taken = False
                    
                    # Calc SL / TP
                    window_highs = np_high[i-sl_lookback+1 : i+1]
                    raw_sl = np.max(window_highs)
                    initial_sl = round_to_tick(raw_sl, tick_sz)
                    
                    if initial_sl <= entry_price:
                        initial_sl = entry_price + tick_sz * 10
                        
                    current_sl = initial_sl
                    risk = current_sl - entry_price
                    partial_tp_price = round_to_tick(entry_price - (risk * tp_ratio), tick_sz)
                    
                    sl_dists.iloc[i] = risk
                    
        return long_entries, long_exits, short_entries, short_exits, exec_prices, sl_dists
