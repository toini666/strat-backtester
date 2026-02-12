from .base import Strategy
import pandas as pd
import numpy as np
import pandas_ta_classic as ta
from typing import Tuple, Dict, Any


class EMA9Retest(Strategy):
    """
    EMA9 Momentum Retest Strategy.
    
    Entry Logic:
    1. N consecutive bullish/bearish candles above/below EMA9 (setup)
       - First candle of the sequence must touch EMA
    2. Price retests EMA within tolerance (retest OK)
    3. Breakout above previous high (long) or below previous low (short) → entry
    
    Exit Logic:
    - Stop loss hit → full exit
    - BE level hit → move SL to entry price
    - TP1 hit → partial exit (tp_partial_pct) + move SL to entry price
    - After partial: close below EMA (long) or above EMA (short) → exit remaining
    
    States:
      0  = FLAT
      1  = SETUP_LONG       5 = SETUP_SHORT
      2  = RETEST_LONG_OK   6 = RETEST_SHORT_OK
      3  = LONG_FULL         7 = SHORT_FULL        (SL original, no EMA exit)
      9  = LONG_BE          10 = SHORT_BE           (SL at BE, no EMA exit)
      4  = LONG_PARTIAL      8 = SHORT_PARTIAL      (after TP1, EMA exit active)
    """
    
    name = "EMA9Retest"
    manual_exit = True
    
    default_params = {
        "ema_length": 9,
        "nb_candles": 3,
        "retest_tolerance": 3,      # ticks
        "max_bars": 10,
        "sl_margin": 3,             # ticks
        "rr_be": 1.0,
        "rr_tp1": 2.0,
        "tp_partial_pct": 0.5,
        "tick_size": 0.25,
        "debug_mode": False
    }
    
    param_ranges = {
        "ema_length": [5, 9, 13, 21],
        "nb_candles": [2, 3, 4, 5],
        "retest_tolerance": [1, 2, 3, 5],
        "max_bars": [5, 10, 15, 20],
        "sl_margin": [0, 2, 3, 5],
        "rr_be": [0.5, 1.0, 1.5],
        "rr_tp1": [1.5, 2.0, 2.5, 3.0],
        "tp_partial_pct": [0.3, 0.5, 0.7],
    }
    
    def generate_signals(
        self, 
        data: pd.DataFrame, 
        params: Dict[str, Any] = None
    ) -> Tuple[pd.Series, pd.Series, pd.Series, pd.Series, pd.Series, pd.Series, pd.Series]:
        p = self.get_params(params)
        
        ema_len = p['ema_length']
        nb_candles = p['nb_candles']
        retest_tol = p['retest_tolerance']
        max_bars = p['max_bars']
        sl_margin = p['sl_margin']
        rr_be = p['rr_be']
        rr_tp1 = p['rr_tp1']
        tp_pct = p['tp_partial_pct']
        tick_sz = p['tick_size']
        debug_mode = p.get('debug_mode', False)
        
        # Minimum data check
        min_length = ema_len + nb_candles + 10
        if len(data) < min_length:
            empty = pd.Series(False, index=data.index)
            zeros = pd.Series(0.0, index=data.index)
            nans = pd.Series(np.nan, index=data.index)
            ones = pd.Series(1.0, index=data.index)
            return empty, empty, empty, empty, zeros, nans, ones
        
        close = data['Close'].values
        open_ = data['Open'].values
        high = data['High'].values
        low = data['Low'].values
        
        def round_to_tick(price):
            return round(price / tick_sz) * tick_sz
        
        # ============================================
        # EMA Calculation
        # ============================================
        ema9 = ta.ema(data['Close'], length=ema_len).values
        
        tol_price = retest_tol * tick_sz
        
        # ============================================
        # Output arrays
        # ============================================
        n = len(data)
        long_entries = np.zeros(n, dtype=bool)
        long_exits = np.zeros(n, dtype=bool)
        short_entries = np.zeros(n, dtype=bool)
        short_exits = np.zeros(n, dtype=bool)
        exec_prices = close.copy().astype(float)
        sl_dists = np.full(n, np.nan)
        exit_ratios = np.ones(n)
        
        # Debug log
        debug_log = []
        STATE_NAMES = {0: 'FLAT', 1: 'SETUP_LONG', 2: 'RETEST_LONG_OK', 3: 'LONG_FULL',
                       4: 'LONG_PARTIAL', 5: 'SETUP_SHORT', 6: 'RETEST_SHORT_OK', 7: 'SHORT_FULL',
                       8: 'SHORT_PARTIAL', 9: 'LONG_BE', 10: 'SHORT_BE'}
        def debug(msg):
            if debug_mode:
                debug_log.append(msg)
        
        # ============================================
        # State Machine Variables (var in PineScript)
        # ============================================
        trade_state = 0
        entry_price = np.nan
        sl_price = np.nan
        tp1_price = np.nan
        be_level = np.nan
        entry_bar = -1
        setup_bar = -1
        
        start_bar = max(ema_len, nb_candles) + 1
        
        for i in range(start_bar, n):
            # Skip if EMA not computed yet
            if np.isnan(ema9[i]) or np.isnan(ema9[i - nb_candles + 1]):
                continue
            
            # ============================================
            # SETUP DETECTION (N consecutive candles)
            # ============================================
            # Check for long setup: N consecutive bullish candles closing above EMA
            long_setup_ok = True
            for k in range(nb_candles):
                idx = i - k
                if not (close[idx] > open_[idx] and close[idx] > ema9[idx]):
                    long_setup_ok = False
                    break
            if long_setup_ok:
                # First candle of sequence (i - nb_candles + 1) must touch EMA: low <= ema9
                first_idx = i - nb_candles + 1
                if low[first_idx] > ema9[first_idx]:
                    long_setup_ok = False
            
            # Check for short setup: N consecutive bearish candles closing below EMA
            short_setup_ok = True
            for k in range(nb_candles):
                idx = i - k
                if not (close[idx] < open_[idx] and close[idx] < ema9[idx]):
                    short_setup_ok = False
                    break
            if short_setup_ok:
                # First candle of sequence must touch EMA: high >= ema9
                first_idx = i - nb_candles + 1
                if high[first_idx] < ema9[first_idx]:
                    short_setup_ok = False
            
            # Debug: log state and setup detection on every bar
            debug(f"{data.index[i]} | state={STATE_NAMES.get(trade_state, trade_state)} | O={open_[i]:.2f} H={high[i]:.2f} L={low[i]:.2f} C={close[i]:.2f} EMA={ema9[i]:.2f} | longSetup={long_setup_ok} shortSetup={short_setup_ok}")
            
            # Debug: warn when a valid setup is blocked by non-FLAT state
            if trade_state != 0 and (long_setup_ok or short_setup_ok):
                debug(f"{data.index[i]} | ⚠ SETUP BLOCKED: state={STATE_NAMES.get(trade_state, trade_state)} prevents {'LONG' if long_setup_ok else 'SHORT'} setup detection")
            
            # ============================================
            # Event flags (reset each bar, like PineScript)
            # ============================================
            ev_signal_long = False
            ev_signal_short = False
            ev_partial_long = False
            ev_partial_short = False
            ev_close_sl_long = False
            ev_close_sl_short = False
            ev_close_be_long = False
            ev_close_be_short = False
            ev_close_ema_long = False
            ev_close_ema_short = False
            ev_move_be_long = False
            ev_move_be_short = False
            ev_partial_price = np.nan
            ev_close_price = np.nan
            
            # ============================================
            # BLOC 1: SETUP / RETEST / ENTRY
            # ============================================
            if trade_state == 0:
                if long_setup_ok:
                    trade_state = 1
                    setup_bar = i
                    debug(f"{data.index[i]} | SETUP LONG detected")
                elif short_setup_ok:
                    trade_state = 5
                    setup_bar = i
                    debug(f"{data.index[i]} | SETUP SHORT detected")
            
            elif trade_state == 1:  # SETUP_LONG
                if i - setup_bar >= max_bars:
                    trade_state = 0
                    debug(f"{data.index[i]} | SETUP LONG expired")
                elif low[i] <= ema9[i] + tol_price:
                    if close[i] > ema9[i]:
                        trade_state = 2
                        debug(f"{data.index[i]} | RETEST LONG OK")
                    else:
                        trade_state = 0
                        debug(f"{data.index[i]} | RETEST LONG failed (close < ema)")
            
            elif trade_state == 2:  # RETEST_LONG_OK
                if i - setup_bar >= max_bars:
                    trade_state = 0
                    debug(f"{data.index[i]} | RETEST LONG expired")
                elif close[i] < ema9[i]:
                    trade_state = 0
                    debug(f"{data.index[i]} | RETEST LONG invalidated (close < ema)")
                elif high[i] > high[i - 1]:
                    # Breakout entry
                    tmp_entry = round_to_tick(high[i - 1] + tick_sz)
                    tmp_sl = round_to_tick(low[i - 1] - sl_margin * tick_sz)
                    risk = tmp_entry - tmp_sl
                    if risk > 0:
                        entry_price = tmp_entry
                        sl_price = tmp_sl
                        tp1_price = round_to_tick(tmp_entry + risk * rr_tp1)
                        be_level = round_to_tick(tmp_entry + risk * rr_be)
                        entry_bar = i
                        trade_state = 3
                        ev_signal_long = True
                        debug(f"{data.index[i]} | >>> ENTER LONG @ {entry_price} SL={sl_price} TP1={tp1_price} BE={be_level}")
                    else:
                        trade_state = 0
                        debug(f"{data.index[i]} | LONG entry rejected (risk <= 0)")
            
            elif trade_state == 5:  # SETUP_SHORT
                if i - setup_bar >= max_bars:
                    trade_state = 0
                    debug(f"{data.index[i]} | SETUP SHORT expired")
                elif high[i] >= ema9[i] - tol_price:
                    if close[i] < ema9[i]:
                        trade_state = 6
                        debug(f"{data.index[i]} | RETEST SHORT OK")
                    else:
                        trade_state = 0
                        debug(f"{data.index[i]} | RETEST SHORT failed (close > ema)")
            
            elif trade_state == 6:  # RETEST_SHORT_OK
                if i - setup_bar >= max_bars:
                    trade_state = 0
                    debug(f"{data.index[i]} | RETEST SHORT expired")
                elif close[i] > ema9[i]:
                    trade_state = 0
                    debug(f"{data.index[i]} | RETEST SHORT invalidated (close > ema)")
                elif low[i] < low[i - 1]:
                    # Breakout entry
                    tmp_entry = round_to_tick(low[i - 1] - tick_sz)
                    tmp_sl = round_to_tick(high[i - 1] + sl_margin * tick_sz)
                    risk = tmp_sl - tmp_entry
                    if risk > 0:
                        entry_price = tmp_entry
                        sl_price = tmp_sl
                        tp1_price = round_to_tick(tmp_entry - risk * rr_tp1)
                        be_level = round_to_tick(tmp_entry - risk * rr_be)
                        entry_bar = i
                        trade_state = 7
                        ev_signal_short = True
                        debug(f"{data.index[i]} | >>> ENTER SHORT @ {entry_price} SL={sl_price} TP1={tp1_price} BE={be_level}")
                    else:
                        trade_state = 0
                        debug(f"{data.index[i]} | SHORT entry rejected (risk <= 0)")
            
            # ============================================
            # BLOC 2: POSITION MANAGEMENT
            # Skip on entry bar to avoid exec_prices conflict
            # (entry + partial exit on same bar corrupts shared arrays)
            # ============================================
            
            is_entry_bar = (i == entry_bar)
            
            if not is_entry_bar:
                # --- LONG_FULL (state 3) ---
                if trade_state == 3:
                    sl_hit = low[i] <= sl_price
                    if sl_hit:
                        ev_close_price = sl_price
                        ev_close_sl_long = True
                        trade_state = 0
                        debug(f"{data.index[i]} | LONG SL HIT @ {sl_price}")
                    elif high[i] >= be_level:
                        ev_move_be_long = True
                        sl_price = entry_price
                        trade_state = 9  # LONG_BE
                        debug(f"{data.index[i]} | LONG BE LEVEL HIT, SL moved to {entry_price}")
                        if high[i] >= tp1_price:
                            ev_partial_price = tp1_price
                            ev_partial_long = True
                            trade_state = 4  # LONG_PARTIAL
                            debug(f"{data.index[i]} | LONG TP1 HIT @ {tp1_price} (partial)")
                
                # --- LONG_BE (state 9) ---
                elif trade_state == 9:
                    if low[i] <= sl_price:
                        ev_close_price = sl_price
                        ev_close_be_long = True
                        trade_state = 0
                        debug(f"{data.index[i]} | LONG BE EXIT @ {sl_price}")
                    elif high[i] >= tp1_price:
                        ev_partial_price = tp1_price
                        ev_partial_long = True
                        trade_state = 4  # LONG_PARTIAL
                        debug(f"{data.index[i]} | LONG TP1 HIT @ {tp1_price} (partial)")
                
                # --- LONG_PARTIAL (state 4) ---
                elif trade_state == 4:
                    if low[i] <= sl_price:
                        ev_close_price = sl_price
                        ev_close_be_long = True
                        trade_state = 0
                        debug(f"{data.index[i]} | LONG PARTIAL BE EXIT @ {sl_price}")
                    elif close[i] < ema9[i]:
                        ev_close_price = round_to_tick(close[i])
                        ev_close_ema_long = True
                        trade_state = 0
                        debug(f"{data.index[i]} | LONG EMA EXIT @ {ev_close_price}")
                
                # --- SHORT_FULL (state 7) ---
                elif trade_state == 7:
                    sl_hit = high[i] >= sl_price
                    if sl_hit:
                        ev_close_price = sl_price
                        ev_close_sl_short = True
                        trade_state = 0
                        debug(f"{data.index[i]} | SHORT SL HIT @ {sl_price}")
                    elif low[i] <= be_level:
                        ev_move_be_short = True
                        sl_price = entry_price
                        trade_state = 10  # SHORT_BE
                        debug(f"{data.index[i]} | SHORT BE LEVEL HIT, SL moved to {entry_price}")
                        if low[i] <= tp1_price:
                            ev_partial_price = tp1_price
                            ev_partial_short = True
                            trade_state = 8  # SHORT_PARTIAL
                            debug(f"{data.index[i]} | SHORT TP1 HIT @ {tp1_price} (partial)")
                
                # --- SHORT_BE (state 10) ---
                elif trade_state == 10:
                    if high[i] >= sl_price:
                        ev_close_price = sl_price
                        ev_close_be_short = True
                        trade_state = 0
                        debug(f"{data.index[i]} | SHORT BE EXIT @ {sl_price}")
                    elif low[i] <= tp1_price:
                        ev_partial_price = tp1_price
                        ev_partial_short = True
                        trade_state = 8  # SHORT_PARTIAL
                        debug(f"{data.index[i]} | SHORT TP1 HIT @ {tp1_price} (partial)")
                
                # --- SHORT_PARTIAL (state 8) ---
                elif trade_state == 8:
                    if high[i] >= sl_price:
                        ev_close_price = sl_price
                        ev_close_be_short = True
                        trade_state = 0
                        debug(f"{data.index[i]} | SHORT PARTIAL BE EXIT @ {sl_price}")
                    elif close[i] > ema9[i]:
                        ev_close_price = round_to_tick(close[i])
                        ev_close_ema_short = True
                        trade_state = 0
                        debug(f"{data.index[i]} | SHORT EMA EXIT @ {ev_close_price}")
            
            # ============================================
            # RECORD SIGNALS
            # ============================================
            
            # ENTRIES
            if ev_signal_long:
                long_entries[i] = True
                exec_prices[i] = entry_price
                sl_dists[i] = entry_price - sl_price  # positive distance
            
            if ev_signal_short:
                short_entries[i] = True
                exec_prices[i] = entry_price
                sl_dists[i] = sl_price - entry_price  # positive distance
            
            # PARTIAL EXITS (TP1)
            if ev_partial_long:
                long_exits[i] = True
                exec_prices[i] = ev_partial_price
                exit_ratios[i] = tp_pct
            
            if ev_partial_short:
                short_exits[i] = True
                exec_prices[i] = ev_partial_price
                exit_ratios[i] = tp_pct
            
            # FULL EXITS (SL, BE, EMA)
            if ev_close_sl_long or ev_close_be_long or ev_close_ema_long:
                long_exits[i] = True
                exec_prices[i] = ev_close_price
                exit_ratios[i] = 1.0
            
            if ev_close_sl_short or ev_close_be_short or ev_close_ema_short:
                short_exits[i] = True
                exec_prices[i] = ev_close_price
                exit_ratios[i] = 1.0
        
        # Write debug log
        if debug_mode and debug_log:
            import os
            log_path = os.path.join(os.path.dirname(__file__), '..', '..', 'ema9retest_debug.log')
            with open(log_path, 'w') as f:
                f.write('\n'.join(debug_log))
            print(f"Debug log written to {log_path} ({len(debug_log)} events)")
        
        # Convert to pandas Series
        idx = data.index
        return (
            pd.Series(long_entries, index=idx),
            pd.Series(long_exits, index=idx),
            pd.Series(short_entries, index=idx),
            pd.Series(short_exits, index=idx),
            pd.Series(exec_prices, index=idx),
            pd.Series(sl_dists, index=idx),
            pd.Series(exit_ratios, index=idx),
        )
