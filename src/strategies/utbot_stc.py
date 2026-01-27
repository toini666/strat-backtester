from .base import Strategy
import pandas as pd
import numpy as np
import pandas_ta_classic as ta
from typing import Tuple, Dict, Any

class UTBotSTC(Strategy):
    """
    UTBot Strategy with STC Filter and Heikin Ashi option.
    Based on Pine Script: 'UTBotSTC'.
    """
    
    name = "UTBotSTC"
    manual_exit = True
    
    default_params = {
        # UTBot Settings
        "key_value": 1.0,
        "atr_period": 10,
        "use_heikin_ashi": False,
        
        # STC Settings
        "stc_length": 12,
        "stc_fast_length": 26,
        "stc_slow_length": 50,
        
        # STC Level Filters
        "stc_min_long": 1.0,
        "stc_max_long": 75.0,
        "stc_min_short": 25.0,
        "stc_max_short": 99.0,
        
        # Position Management
        "stop_ticks": 3,
        "risk_reward": 2.0,
        "tick_size": 0.25
    }

    def generate_signals(
        self, 
        data: pd.DataFrame, 
        params: Dict[str, Any] = None
    ) -> Tuple[pd.Series, pd.Series, pd.Series, pd.Series, pd.Series, pd.Series, pd.Series]:
        p = self.get_params(params)
        
        # Ensure we have enough data
        if len(data) < p['stc_slow_length']:
            empty = pd.Series(False, index=data.index)
            zeros = pd.Series(0.0, index=data.index)
            nans = pd.Series(np.nan, index=data.index)
            return empty, empty, empty, empty, zeros, nans, nans

        calc_close = data['Close']
        calc_open = data['Open']
        calc_high = data['High']
        calc_low = data['Low']
        
        # 1. Heikin Ashi Calculation (Matches UTBotHeikin logic)
        if p['use_heikin_ashi']:
            ha_close = (data['Open'] + data['High'] + data['Low'] + data['Close']) / 4
            
            # HA Open requires iteration
            np_ha_open = np.zeros(len(data))
            np_ha_open[0] = data['Open'].values[0]
            np_ha_close = ha_close.values
            
            for i in range(1, len(data)):
                np_ha_open[i] = (np_ha_open[i-1] + np_ha_close[i-1]) / 2
                
            ha_open = pd.Series(np_ha_open, index=data.index)
            
            # HA High/Low
            ha_high = pd.DataFrame({'a': data['High'], 'b': ha_open, 'c': ha_close}).max(axis=1)
            ha_low = pd.DataFrame({'a': data['Low'], 'b': ha_open, 'c': ha_close}).min(axis=1)
            
            # Use HA for calculations
            calc_open = ha_open
            calc_high = ha_high
            calc_low = ha_low
            calc_close = ha_close

        # 2. UTBot Calculation (Vectorized Trailing Stop)
        # Identical logic to UTBotHeikin but using params from this strategy
        xATR = ta.atr(calc_high, calc_low, calc_close, length=p['atr_period'])
        nLoss = p['key_value'] * xATR
        
        np_src = calc_close.values
        np_nLoss = nLoss.values
        np_trail = np.zeros(len(data))
        
        # Initialize first Value
        np_trail[0] = np_src[0]
        
        # Note: logic requires prev state.
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
        
        # Generate Raw Signals
        prev_src = calc_close.shift(1)
        prev_trail = xATRTrailingStop.shift(1)
        
        utbot_long = (calc_close > xATRTrailingStop) & (prev_src < prev_trail)
        utbot_short = (calc_close < xATRTrailingStop) & (prev_src > prev_trail)
        
        # 3. STC Calculation (Manual Implementation to match Pine)
        # Pine Logic:
        # 1. MACD
        # 2. %K of MACD -> Smoothed (%D) = PF
        # 3. %K of PF -> Smoothed (%D) = PFF2 (Final STC)
        
        # 1. MACD
        fast_ma = ta.ema(calc_close, length=p['stc_fast_length'])
        slow_ma = ta.ema(calc_close, length=p['stc_slow_length'])
        macd_val = fast_ma - slow_ma
        
        stc_len = p['stc_length']
        
        # Prepare for Loops - Convert to numpy for performance
        np_macd = macd_val.fillna(0).values
        
        # Helper to get rolling min/max efficiently
        macd_s = pd.Series(np_macd)
        low_macd = macd_s.rolling(window=stc_len).min().fillna(0).values
        high_macd = macd_s.rolling(window=stc_len).max().fillna(0).values
        
        # Arrays for PF
        pf_series = np.zeros(len(data))
        pff_prev = 0.0 # Holds "nz(pff[1])"
        pf_prev = 0.0  # Holds "nz(pf[1])"
        factor = 0.5
        
        for i in range(len(data)):
             if i < stc_len: 
                 # Not enough data for rolling
                 continue
                 
             m_val = np_macd[i]
             l_val = low_macd[i]
             h_val = high_macd[i]
             rng1 = h_val - l_val
             
             # pff := range1 > 0 ? (macdVal - lowest) / range1 * 100 : nz(pff[1])
             if rng1 > 0:
                 pff = (m_val - l_val) / rng1 * 100
             else:
                 pff = pff_prev # Keep previous
                 
             pff_prev = pff
             
             # pf := na(pf[1]) ? pff : pf[1] + factor * (pff - pf[1])
             # In loop, pf_prev is pf[1]
             pf = pf_prev + factor * (pff - pf_prev)
             pf_prev = pf
             pf_series[i] = pf

        # Step 2: STC Final (Recursive on PF)
        pf_s = pd.Series(pf_series)
        low_pf = pf_s.rolling(window=stc_len).min().fillna(0).values
        high_pf = pf_s.rolling(window=stc_len).max().fillna(0).values
        
        stc_final = np.zeros(len(data))
        pfff_prev = 0.0
        pff2_prev = 0.0
        
        for i in range(len(data)):
             if i < stc_len:
                 continue
                 
             val = pf_series[i]
             l_val = low_pf[i]
             h_val = high_pf[i]
             rng2 = h_val - l_val
             
             if rng2 > 0:
                 pfff = (val - l_val) / rng2 * 100
             else:
                 pfff = pfff_prev
                 
             pfff_prev = pfff
             
             pff2 = pff2_prev + factor * (pfff - pff2_prev)
             pff2_prev = pff2
             stc_final[i] = pff2
             
        stc_val = pd.Series(stc_final, index=data.index)
             
        # STC Conditions
        stc_dates = stc_val.index
        stc_prev = stc_val.shift(1)
        
        stc_rising = stc_val > stc_prev
        stc_falling = stc_val < stc_prev
        
        stc_valid_long = (stc_val >= p['stc_min_long']) & (stc_val <= p['stc_max_long']) & stc_rising
        stc_valid_short = (stc_val >= p['stc_min_short']) & (stc_val <= p['stc_max_short']) & stc_falling
        
        # 4. Filtered Entry Signals
        long_signal = utbot_long & stc_valid_long
        short_signal = utbot_short & stc_valid_short
        
        # 5. Position Management (Fixed SL/TP)
        long_entries = pd.Series(False, index=data.index)
        long_exits = pd.Series(False, index=data.index)
        short_entries = pd.Series(False, index=data.index)
        short_exits = pd.Series(False, index=data.index)
        
        # Initialize exec_prices with Real Close to avoid leaking HA values
        real_close = data['Close']
        real_high = data['High']
        real_low = data['Low']
        
        exec_prices = real_close.copy() 
        sl_dists = pd.Series(np.nan, index=data.index)
        exit_ratios = pd.Series(1.0, index=data.index)
        
        # Helper for rounding
        tick_sz = p['tick_size'] if p['tick_size'] > 0 else 0.25
        def round_to_tick(price):
             return round(price / tick_sz) * tick_sz
        
        # Loop variables
        in_pos = False
        pos_side = 0
        entry_price = 0.0
        stop_price = 0.0
        tp_price = 0.0
        stop_ticks = p['stop_ticks']
        rr = p['risk_reward']
        
        np_long_sig = long_signal.values
        np_short_sig = short_signal.values
        
        # Use simple iteration for State Machine
        for i in range(1, len(data)):
            
            # --- Exits ---
            if in_pos:
                curr_low = real_low.iloc[i]
                curr_high = real_high.iloc[i]
                
                if pos_side == 1: # Long
                    if curr_low <= stop_price:
                        # SL Hit
                        long_exits.iloc[i] = True
                        exec_prices.iloc[i] = stop_price
                        in_pos = False
                        pos_side = 0
                    elif curr_high >= tp_price:
                        # TP Hit
                        long_exits.iloc[i] = True
                        exec_prices.iloc[i] = tp_price
                        in_pos = False
                        pos_side = 0
                        
                elif pos_side == -1: # Short
                    if curr_high >= stop_price:
                        # SL Hit
                        short_exits.iloc[i] = True
                        exec_prices.iloc[i] = stop_price
                        in_pos = False
                        pos_side = 0
                    elif curr_low <= tp_price:
                        # TP Hit
                        short_exits.iloc[i] = True
                        exec_prices.iloc[i] = tp_price
                        in_pos = False
                        pos_side = 0

            # --- Entries ---
            if not in_pos:
                # Entries are taken at Close of Bar (or Open of next - here simulation uses Close of signal bar)
                # Pine: "if longSignal ... inPosition := true ... entryPrice := close"
                # This implies Immediate Entry at Close of Signal Bar.
                
                if np_long_sig[i]:
                    entry_p = round_to_tick(real_close.iloc[i])
                    
                    # Calculate SL/TP based on SIGNAL CANDLE (current bar i)
                    # Pine: signalLow = low; stopPrice := roundToTick(signalLow - stopTicks * minTick)
                    sig_low = real_low.iloc[i]
                    stop_p = round_to_tick(sig_low - stop_ticks * tick_sz)
                    risk_amt = entry_p - stop_p
                    tp_p = round_to_tick(entry_p + risk_amt * rr)
                    
                    if risk_amt > 0:
                        long_entries.iloc[i] = True
                        exec_prices.iloc[i] = entry_p
                        in_pos = True
                        pos_side = 1
                        entry_price = entry_p
                        stop_price = stop_p
                        tp_price = tp_p
                        sl_dists.iloc[i] = risk_amt
                    
                elif np_short_sig[i]:
                    entry_p = round_to_tick(real_close.iloc[i])
                    
                    # Pine: signalHigh = high; stopPrice := roundToTick(signalHigh + stopTicks * minTick)
                    sig_high = real_high.iloc[i]
                    stop_p = round_to_tick(sig_high + stop_ticks * tick_sz)
                    risk_amt = stop_p - entry_p
                    tp_p = round_to_tick(entry_p - risk_amt * rr)
                    
                    if risk_amt > 0:
                        short_entries.iloc[i] = True
                        exec_prices.iloc[i] = entry_p
                        in_pos = True
                        pos_side = -1
                        entry_price = entry_p
                        stop_price = stop_p
                        tp_price = tp_p
                        sl_dists.iloc[i] = risk_amt

        return long_entries, long_exits, short_entries, short_exits, exec_prices, sl_dists, exit_ratios
