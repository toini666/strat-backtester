from .base import Strategy
import pandas as pd
import numpy as np
import pandas_ta_classic as ta
from typing import Tuple, Dict, Any
import warnings

# Suppress FutureWarnings from pandas-ta MFI calculation
warnings.filterwarnings('ignore', category=FutureWarning, module='pandas_ta_classic.volume.mfi')


class DeltaDiv(Strategy):
    """
    DeltaDiv Strategy based on 4Kings Oscillator.
    
    Entry Logic:
    1. Circle detected (reversal signal via volume + oscillator + MFI)
    2. Divergence confirmed within max_bars_since_circle
    3. Delta (osc + mfi aligned) seen and then extinguished -> entry
    
    Exit Logic:
    - Stop loss hit -> full exit
    - Take profit hit -> partial exit (tp_partial_pct) + move SL to break-even
    - After TP partial: breakeven hit OR opposite delta signal -> full exit
    """
    
    name = "DeltaDiv"
    manual_exit = True
    
    default_params = {
        # 4Kings Oscillator Core
        "hyper_wave_length": 5,
        "signal_type": "SMA",  # SMA or EMA
        "signal_length": 3,
        "divergence_sensibility": 20,
        
        # Smart Money Flow
        "mf_length": 35,
        "mf_smooth": 6,
        
        # Reversal
        "reversal_factor": 4,
        
        # Strategy Settings (User-requested configurable params)
        "stop_loss_lookback": 5,
        "tp_rr": 2.0,
        "tp_partial_pct": 0.5,
        "max_bars_since_circle": 15,
        
        # Tick size
        "tick_size": 0.25,
        
        # Debug mode - set to True to enable debug output
        "debug_mode": False
    }
    
    # Parameter ranges for optimization
    param_ranges = {
        # Core oscillator params
        "hyper_wave_length": [3, 5, 7, 10],
        "divergence_sensibility": [20, 25, 30, 35, 40],
        "reversal_factor": [2, 3, 4, 5, 6],
        # Position management params
        "stop_loss_lookback": [3, 5, 7, 10],
        "tp_rr": [1.5, 2.0, 2.5, 3.0],
        "tp_partial_pct": [0.3, 0.5, 0.7],
        "max_bars_since_circle": [10, 15, 20, 25],
    }
    
    def generate_signals(
        self, 
        data: pd.DataFrame, 
        params: Dict[str, Any] = None
    ) -> Tuple[pd.Series, pd.Series, pd.Series, pd.Series, pd.Series, pd.Series, pd.Series]:
        p = self.get_params(params)
        
        # Ensure we have enough data
        min_length = max(p['hyper_wave_length'], p['mf_length'], p['stop_loss_lookback']) + 50
        if len(data) < min_length:
            empty = pd.Series(False, index=data.index)
            zeros = pd.Series(0.0, index=data.index)
            nans = pd.Series(np.nan, index=data.index)
            ones = pd.Series(1.0, index=data.index)
            return empty, empty, empty, empty, zeros, nans, ones
        
        close = data['Close']
        open_ = data['Open']
        high = data['High']
        low = data['Low']
        volume = data['Volume']
        hl2 = (high + low) / 2
        
        # Parameters
        mL = p['hyper_wave_length']
        sT = p['signal_type']
        sL = p['signal_length']
        dvT = p['divergence_sensibility']
        mfL = p['mf_length']
        mfS = p['mf_smooth']
        rsF = p['reversal_factor']
        sl_lookback = p['stop_loss_lookback']
        tp_rr = p['tp_rr']
        tp_pct = p['tp_partial_pct']
        max_bars_circle = p['max_bars_since_circle']
        tick_sz = p['tick_size']
        debug_mode = p.get('debug_mode', False)
        
        # Debug log file
        debug_log = []
        
        def debug(msg):
            if debug_mode:
                debug_log.append(msg)
        
        def round_to_tick(price, tick_size):
            return round(price / tick_size) * tick_size
        
        # ============================================
        # 1. PRE-CALCULATE OSCILLATOR SERIES
        # ============================================
        
        hi = high.rolling(window=mL).max()
        lo = low.rolling(window=mL).min()
        av = ta.sma(hl2, length=mL)
        avg_hla = (hi + lo + av) / 3
        raw_osc = (close - avg_hla) / (hi - lo + 1e-10) * 100
        
        # Linear regression for oscillator
        osc_linreg = pd.Series(np.nan, index=data.index)
        np_raw = raw_osc.values
        for i in range(mL - 1, len(data)):
            window = np_raw[i - mL + 1:i + 1]
            if not np.any(np.isnan(window)):
                x = np.arange(mL)
                try:
                    coeffs = np.polyfit(x, window, 1)
                    osc_linreg.iloc[i] = coeffs[0] * (mL - 1) + coeffs[1]
                except:
                    osc_linreg.iloc[i] = window[-1]
        
        osc_sig = ta.ema(osc_linreg, length=sL)
        osc_sgd = ta.sma(osc_sig, length=2) if sT == "SMA" else ta.ema(osc_sig, length=2)
        
        # ============================================
        # 2. PRE-CALCULATE MFI SERIES
        # ============================================
        # CRITICAL: TradingView uses ta.mfi(hl2, length) with hl2 as source
        # pandas-ta uses hlc3 internally, so we must calculate MFI manually
        
        # MFI calculation using hl2 as typical price (matching TradingView)
        # MFI = 100 - (100 / (1 + positive_flow / negative_flow))
        typical_price = hl2  # TradingView uses hl2, not hlc3!
        raw_money_flow = typical_price * volume
        
        # Calculate positive and negative money flow
        tp_change = typical_price.diff()
        positive_flow = pd.Series(0.0, index=data.index)
        negative_flow = pd.Series(0.0, index=data.index)
        
        positive_flow = raw_money_flow.where(tp_change > 0, 0.0)
        negative_flow = raw_money_flow.where(tp_change < 0, 0.0)
        
        # Sum over mfL period
        positive_sum = positive_flow.rolling(window=mfL).sum()
        negative_sum = negative_flow.rolling(window=mfL).sum()
        
        # Calculate MFI
        money_flow_ratio = positive_sum / (negative_sum + 1e-10)  # Avoid division by zero
        mfi_raw = 100 - (100 / (1 + money_flow_ratio))
        
        # Apply smoothing (SMA) and center around 0 (subtract 50)
        mfi = ta.sma(mfi_raw - 50, length=mfS)

        
        # ============================================
        # 3. PRE-CALCULATE CIRCLE CONDITIONS
        # ============================================
        
        vMA = ta.sma(volume, length=7)
        rsi_vol = ta.rsi(vMA, length=7) - 50
        
        vol_mult_major = 1 + (rsF / 10) if rsF != 10 else 2
        vol_mult_minor = rsF / 10 if rsF != 10 else 2
        
        tMj = volume > vMA * vol_mult_major
        tMn = (volume > vMA * vol_mult_minor) & (~tMj)
        
        # Minor circles
        mnBL = tMn & (osc_sig < -20) & (osc_sig < osc_sgd) & (rsi_vol < -20)
        mnBR = tMn & (osc_sig > 20) & (osc_sig > osc_sgd) & (rsi_vol > 20)
        
        # ============================================
        # 4. PRE-CALCULATE CROSSOVER/CROSSUNDER
        # ============================================
        
        cross_under = (osc_sig.shift(1) > osc_sgd.shift(1)) & (osc_sig <= osc_sgd)
        cross_over = (osc_sig.shift(1) < osc_sgd.shift(1)) & (osc_sig >= osc_sgd)
        
        # ============================================
        # 5. PRE-CALCULATE DELTA STATES
        # ============================================
        
        delta_long_on = (osc_sig > 0) & (mfi > 0)
        delta_short_on = (osc_sig < 0) & (mfi < 0)
        
        # ============================================
        # 6. UNIFIED LOOP - ALL STATE MANAGEMENT
        # ============================================
        
        long_entries = pd.Series(False, index=data.index)
        long_exits = pd.Series(False, index=data.index)
        short_entries = pd.Series(False, index=data.index)
        short_exits = pd.Series(False, index=data.index)
        exec_prices = close.copy()
        sl_dists = pd.Series(np.nan, index=data.index)
        exit_ratios = pd.Series(1.0, index=data.index)
        
        # Convert to numpy for speed
        np_osc_sig = osc_sig.values
        np_osc_sgd = osc_sgd.values
        np_mfi = mfi.values  # For debug logging
        np_open = open_.values
        np_close = close.values
        np_high = high.values
        np_low = low.values
        np_cross_under = cross_under.values
        np_cross_over = cross_over.values
        np_mnBL = mnBL.values
        np_mnBR = mnBR.values
        np_delta_long_on = delta_long_on.values
        np_delta_short_on = delta_short_on.values

        
        # ========================================
        # PERSISTENT STATE VARIABLES (like PineScript var)
        # ========================================
        
        # Position state
        in_pos = False
        is_long = False
        entry_price = 0.0
        stop_loss = 0.0
        take_profit = 0.0
        entry_bar = -1
        tp_partial_hit = False
        
        # Setup tracking (var in PineScript)
        circle_detected = False
        circle_long = False
        circle_bar_idx = -1
        setup_ready = False
        setup_long = False
        delta_has_been_on = False
        
        # Divergence state (var div = DivData.new(na, na, na) in PineScript)
        div_n = np.nan
        div_src = np.nan
        div_p = np.nan
        
        # Previous bar delta states
        delta_long_prev = False
        delta_short_prev = False
        
        # Start from adequate lookback
        start_bar = max(sl_lookback, mL, mfL + mfS) + 5
        
        for i in range(start_bar, len(data)):
            # Current bar values
            curr_close = np_close[i]
            curr_high = np_high[i]
            curr_low = np_low[i]
            curr_osc_sig = np_osc_sig[i] if not np.isnan(np_osc_sig[i]) else 0
            curr_osc_sgd = np_osc_sgd[i] if not np.isnan(np_osc_sgd[i]) else 0
            prev_osc_sig = np_osc_sig[i-1] if i > 0 and not np.isnan(np_osc_sig[i-1]) else 0
            prev_osc_sgd = np_osc_sgd[i-1] if i > 0 and not np.isnan(np_osc_sgd[i-1]) else 0
            curr_delta_long_on = np_delta_long_on[i]
            curr_delta_short_on = np_delta_short_on[i]
            is_cross_under = np_cross_under[i]
            is_cross_over = np_cross_over[i]
            
            # ----------------------------------------
            # DIVERGENCE DETECTION (inline, not separate loop)
            # ----------------------------------------
            div_bullish = False
            div_bearish = False
            
            # Bearish divergence (for SHORT)
            if curr_osc_sig > dvT and is_cross_under:
                mx = max(curr_osc_sig, curr_osc_sgd, prev_osc_sig, prev_osc_sgd)
                mxid = 1 if (mx == prev_osc_sig or mx == prev_osc_sgd) else 0
                max_oc = max(np_open[i - mxid], np_close[i - mxid])
                
                if np.isnan(div_src):
                    div_n = i - mxid
                    div_src = max_oc
                    div_p = mx
                else:
                    osc_at_mxid = np_osc_sig[i - mxid] if not np.isnan(np_osc_sig[i - mxid]) else 0
                    if max_oc > div_src and not (osc_at_mxid > div_p):
                        div_bearish = True
                        div_n = np.nan
                        div_src = np.nan
                        div_p = np.nan
                    else:
                        div_n = i - mxid
                        div_src = max_oc
                        div_p = mx
            
            # Bullish divergence (for LONG)
            if curr_osc_sig < -dvT and is_cross_over:
                mn = min(curr_osc_sig, curr_osc_sgd, prev_osc_sig, prev_osc_sgd)
                mnid = 1 if (mn == prev_osc_sig or mn == prev_osc_sgd) else 0
                min_oc = min(np_open[i - mnid], np_close[i - mnid])
                
                if np.isnan(div_src):
                    div_n = i - mnid
                    div_src = min_oc
                    div_p = mn
                else:
                    osc_at_mnid = np_osc_sig[i - mnid] if not np.isnan(np_osc_sig[i - mnid]) else 0
                    if min_oc < div_src and not (osc_at_mnid < div_p):
                        div_bullish = True
                        div_n = np.nan
                        div_src = np.nan
                        div_p = np.nan
                    else:
                        div_n = i - mnid
                        div_src = min_oc
                        div_p = mn
            
            # ----------------------------------------
            # CIRCLE DETECTION
            # ----------------------------------------
            if np_mnBL[i] and not in_pos and not setup_ready:
                circle_detected = True
                circle_long = True
                circle_bar_idx = i
                debug(f"{data.index[i]} | CIRCLE BULLISH detected")
                
            if np_mnBR[i] and not in_pos and not setup_ready:
                circle_detected = True
                circle_long = False
                circle_bar_idx = i
                debug(f"{data.index[i]} | CIRCLE BEARISH detected")
            
            # ----------------------------------------
            # DIVERGENCE AFTER CIRCLE -> SETUP READY
            # ----------------------------------------

            # CRITICAL: Match PineScript exactly - Check Delta and MFI immediately on Divergence
            if circle_detected and div_bullish and circle_long and not in_pos:
                bars_since_circle = i - circle_bar_idx
                if bars_since_circle <= max_bars_circle:
                    # LONG setup requires: SHORT delta ON (osc<0, mfi<0) AND MFI negative
                    delta_ok = curr_delta_short_on
                    mfi_ok = np_mfi[i] < 0 if not np.isnan(np_mfi[i]) else False
                    
                    if delta_ok and mfi_ok:
                        setup_ready = True
                        setup_long = True
                        delta_has_been_on = True  # User change: Delta is already on, mark it as seen
                        debug(f"{data.index[i]} | SETUP LONG READY | bars_since_circle={bars_since_circle} | Delta ON & MFI OK")
                    else:
                        # Conditions not met - cancel setup
                        circle_detected = False
                        circle_bar_idx = -1
                        setup_ready = False
                        delta_has_been_on = False
                        div_n = np.nan
                        div_src = np.nan
                        div_p = np.nan
                        debug(f"{data.index[i]} | CANCEL LONG setup | Delta/MFI conditions not met")
                    
            if circle_detected and div_bearish and not circle_long and not in_pos:
                bars_since_circle = i - circle_bar_idx
                if bars_since_circle <= max_bars_circle:
                    # SHORT setup requires: LONG delta ON (osc>0, mfi>0) AND MFI positive
                    delta_ok = curr_delta_long_on
                    mfi_ok = np_mfi[i] > 0 if not np.isnan(np_mfi[i]) else False
                    
                    if delta_ok and mfi_ok:
                        setup_ready = True
                        setup_long = False
                        delta_has_been_on = True  # User change: Delta is already on, mark it as seen
                        debug(f"{data.index[i]} | SETUP SHORT READY | bars_since_circle={bars_since_circle} | Delta ON & MFI OK")
                    else:
                        # Conditions not met - cancel setup
                        circle_detected = False
                        circle_bar_idx = -1
                        setup_ready = False
                        delta_has_been_on = False
                        div_n = np.nan
                        div_src = np.nan
                        div_p = np.nan
                        debug(f"{data.index[i]} | CANCEL SHORT setup | Delta/MFI conditions not met")
            
            # ----------------------------------------
            # DELTA TRACKING AND INVALIDATION
            # ----------------------------------------
            if setup_ready and setup_long and not in_pos:
                if curr_delta_short_on:
                    if delta_has_been_on and not delta_short_prev:
                        # Delta relighting - invalidate setup
                        debug(f"{data.index[i]} | INVALIDATE LONG setup (delta relit)")
                        setup_ready = False
                        circle_detected = False
                        circle_bar_idx = -1
                        delta_has_been_on = False
                    else:
                        delta_has_been_on = True
                        debug(f"{data.index[i]} | delta_has_been_on set to True (delta SHORT ON)")
            
            if setup_ready and not setup_long and not in_pos:
                if curr_delta_long_on:
                    if delta_has_been_on and not delta_long_prev:
                        # Delta relighting - invalidate setup
                        debug(f"{data.index[i]} | INVALIDATE SHORT setup (delta relit)")
                        setup_ready = False
                        circle_detected = False
                        circle_bar_idx = -1
                        delta_has_been_on = False
                    else:
                        delta_has_been_on = True
                        debug(f"{data.index[i]} | delta_has_been_on set to True (delta LONG ON)")
            
            # ----------------------------------------
            # ENTRY LOGIC
            # ----------------------------------------
            enter_long = False
            enter_short = False
            
            # Get current mfi value for debug
            curr_mfi = np_mfi[i] if not np.isnan(np_mfi[i]) else 0
            
            # Debug entry conditions with osc/mfi values
            if setup_ready and setup_long and not in_pos:
                debug(f"{data.index[i]} | LONG check: dHBO={delta_has_been_on}, dS_prev={delta_short_prev}, dS_curr={curr_delta_short_on} | osc={curr_osc_sig:.2f}, mfi={curr_mfi:.2f}")
            if setup_ready and not setup_long and not in_pos:
                debug(f"{data.index[i]} | SHORT check: dHBO={delta_has_been_on}, dL_prev={delta_long_prev}, dL_curr={curr_delta_long_on} | osc={curr_osc_sig:.2f}, mfi={curr_mfi:.2f}")

            
            if setup_ready and setup_long and not in_pos and delta_has_been_on:
                if delta_short_prev and not curr_delta_short_on:
                    enter_long = True
                    debug(f"{data.index[i]} | >>> ENTER LONG!")
                    
            if setup_ready and not setup_long and not in_pos and delta_has_been_on:
                if delta_long_prev and not curr_delta_long_on:
                    enter_short = True
                    debug(f"{data.index[i]} | >>> ENTER SHORT!")
            
            # ----------------------------------------
            # EXECUTE ENTRY
            # ----------------------------------------

            if enter_long and not in_pos:
                in_pos = True
                is_long = True
                entry_price = round_to_tick(curr_close, tick_sz)
                entry_bar = i
                
                window_lows = np_low[i - sl_lookback + 1:i + 1]
                stop_loss = round_to_tick(np.min(window_lows), tick_sz)
                
                risk = entry_price - stop_loss
                if risk <= 0:
                    risk = tick_sz * 10
                take_profit = round_to_tick(entry_price + (risk * tp_rr), tick_sz)
                
                tp_partial_hit = False
                
                # Reset setup tracking
                circle_detected = False
                circle_bar_idx = -1
                setup_ready = False
                delta_has_been_on = False
                
                long_entries.iloc[i] = True
                exec_prices.iloc[i] = entry_price
                sl_dists.iloc[i] = risk
                
            if enter_short and not in_pos:
                in_pos = True
                is_long = False
                entry_price = round_to_tick(curr_close, tick_sz)
                entry_bar = i
                
                window_highs = np_high[i - sl_lookback + 1:i + 1]
                stop_loss = round_to_tick(np.max(window_highs), tick_sz)
                
                risk = stop_loss - entry_price
                if risk <= 0:
                    risk = tick_sz * 10
                take_profit = round_to_tick(entry_price - (risk * tp_rr), tick_sz)
                
                tp_partial_hit = False
                
                # Reset setup tracking
                circle_detected = False
                circle_bar_idx = -1
                setup_ready = False
                delta_has_been_on = False
                
                short_entries.iloc[i] = True
                exec_prices.iloc[i] = entry_price
                sl_dists.iloc[i] = risk
            
            # ----------------------------------------
            # EXIT LOGIC
            # ----------------------------------------
            if in_pos and i > entry_bar:
                hit_stop_loss = False
                hit_breakeven = False
                opposite_signal = False
                
                if is_long:
                    if curr_low <= stop_loss:
                        hit_stop_loss = True
                    
                    if not tp_partial_hit and curr_high >= take_profit:
                        tp_partial_hit = True
                        stop_loss = entry_price
                        
                        long_exits.iloc[i] = True
                        exec_prices.iloc[i] = take_profit
                        exit_ratios.iloc[i] = tp_pct
                        
                        delta_long_prev = curr_delta_long_on
                        delta_short_prev = curr_delta_short_on
                        continue
                    
                    if tp_partial_hit and curr_low <= entry_price:
                        hit_breakeven = True
                    
                    if delta_long_prev and not curr_delta_long_on:
                        opposite_signal = True
                        
                else:  # SHORT
                    if curr_high >= stop_loss:
                        hit_stop_loss = True
                    
                    if not tp_partial_hit and curr_low <= take_profit:
                        tp_partial_hit = True
                        stop_loss = entry_price
                        
                        short_exits.iloc[i] = True
                        exec_prices.iloc[i] = take_profit
                        exit_ratios.iloc[i] = tp_pct
                        
                        delta_long_prev = curr_delta_long_on
                        delta_short_prev = curr_delta_short_on
                        continue
                    
                    if tp_partial_hit and curr_high >= entry_price:
                        hit_breakeven = True
                    
                    if delta_short_prev and not curr_delta_short_on:
                        opposite_signal = True
                
                close_position = hit_stop_loss or opposite_signal or hit_breakeven
                
                if close_position:
                    if is_long:
                        long_exits.iloc[i] = True
                        if hit_stop_loss:
                            exec_prices.iloc[i] = stop_loss
                        elif hit_breakeven:
                            exec_prices.iloc[i] = entry_price
                        else:
                            exec_prices.iloc[i] = round_to_tick(curr_close, tick_sz)
                    else:
                        short_exits.iloc[i] = True
                        if hit_stop_loss:
                            exec_prices.iloc[i] = stop_loss
                        elif hit_breakeven:
                            exec_prices.iloc[i] = entry_price
                        else:
                            exec_prices.iloc[i] = round_to_tick(curr_close, tick_sz)
                    
                    in_pos = False
                    is_long = False
                    entry_price = 0.0
                    stop_loss = 0.0
                    take_profit = 0.0
                    entry_bar = -1
                    tp_partial_hit = False
                    
                    # Reset setup tracking after exit
                    circle_detected = False
                    circle_bar_idx = -1
                    setup_ready = False
                    delta_has_been_on = False
            
            # Update previous delta states at END of bar
            delta_long_prev = curr_delta_long_on
            delta_short_prev = curr_delta_short_on
        
        # Write debug log to file if debug mode enabled
        if debug_mode and debug_log:
            import os
            log_path = os.path.join(os.path.dirname(__file__), '..', '..', 'deltadiv_debug.log')
            with open(log_path, 'w') as f:
                f.write('\n'.join(debug_log))
            print(f"Debug log written to {log_path} ({len(debug_log)} events)")
        
        return long_entries, long_exits, short_entries, short_exits, exec_prices, sl_dists, exit_ratios
