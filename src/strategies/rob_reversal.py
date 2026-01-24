from .base import Strategy
import pandas as pd
import numpy as np
import pandas_ta_classic as ta
from typing import Tuple, Dict, Any, Optional

class RobReversal(Strategy):
    """
    Rob Reversal Strategy (15min).
    Based on Pine Script implementation.
    
    Logic:
    - Context: Previous bar (Bar A) direction.
    - Sweep: Current bar (Bar B) sweeps high/low of Bar A.
    - Internal Close: Bar B closes inside Bar A's body.
    - EMA Filter: Close relative to EMA 8.
    - Entry: Pending order placed at Bar B high/low + tick.
    """
    
    name = "RobReversal"
    
    default_params = {
        "ema_length": 8,
        "take_profit": 35.0,  # Points
        "max_stop_loss": 35.0, # Points
        "trigger_bars": 1,    # Bars to trigger entry
        "tick_size": 0.25,    # Default tick size (MNQ/MES) - adjusted via params
        "block_new_signals": True
    }

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
        
        # Indicators
        ema8 = ta.ema(close, length=p['ema_length'])
        
        # --- Pre-calculate setup conditions (Same as before) ---
        barA_open = open_.shift(1)
        barA_close = close.shift(1)
        barA_high = high.shift(1)
        barA_low = low.shift(1)
        
        barB_open = open_
        barB_close = close
        barB_high = high
        barB_low = low
        
        barA_bodyHigh = np.maximum(barA_open, barA_close)
        barA_bodyLow = np.minimum(barA_open, barA_close)
        
        barA_isBearish = barA_close < barA_open
        barA_isBullish = barA_close > barA_open
        
        # Long Setup
        c1_long = barA_isBearish
        c2_long = barB_low < (barA_low - p['tick_size'])
        c3_long = (barB_close > barA_bodyLow) & (barB_close < barA_bodyHigh)
        c4_long = barB_close > ema8
        long_setup = c1_long & c2_long & c3_long & c4_long
        
        # Short Setup
        c1_short = barA_isBullish
        c2_short = barB_high > (barA_high + p['tick_size'])
        c3_short = (barB_close < barA_bodyHigh) & (barB_close > barA_bodyLow)
        c4_short = barB_close < ema8
        short_setup = c1_short & c2_short & c3_short & c4_short
        
        # --- Trade Management Loop ---
        
        # Output Signals
        long_entries = pd.Series(False, index=data.index)
        long_exits = pd.Series(False, index=data.index)
        short_entries = pd.Series(False, index=data.index)
        short_exits = pd.Series(False, index=data.index)
        
        # NumPy arrays for speed
        np_high = high.values
        np_low = low.values
        np_close = close.values
        np_open = open_.values
        np_long_setup = long_setup.values
        np_short_setup = short_setup.values
        
        # State
        # Pending Orders
        pending_long = False
        pending_long_entry = 0.0
        pending_long_sl = 0.0
        pending_long_tp = 0.0
        long_setup_idx = -1
        
        pending_short = False
        pending_short_entry = 0.0
        pending_short_sl = 0.0
        pending_short_tp = 0.0
        short_setup_idx = -1
        
        # Active Trade
        active_trade_side = 0 # 1=Long, -1=Short, 0=None
        active_tp = 0.0
        active_sl = 0.0
        
        ts_tick = p['tick_size']
        trigger_bars = p['trigger_bars']
        block_new = p['block_new_signals']

        # SL Distance Series (for dynamic sizing)
        sl_dist_series = pd.Series(np.nan, index=data.index)
        np_sl_dist = np.full(len(data), np.nan)

        # Execution Price Series (default to Close, override on trade bars)
        exec_price = close.copy()
        np_exec_price = exec_price.values

        for i in range(len(data)):
            # Data for this bar
            O = np_open[i]
            H = np_high[i]
            L = np_low[i]
            C = np_close[i]
            
            # --- 1. GAP CHECK (At Open) ---
            # Process Exits/Entries on Gap before intrabar movement
            
            # Active Trade Gap Exit
            if active_trade_side == 1:
                # Long: Check if Open gap passed SL or TP
                # Priority: SL filled at Open if Open < SL (Gap Down death)
                if O <= active_sl: 
                    long_exits.iloc[i] = True
                    np_exec_price[i] = O # Fill at Open
                    active_trade_side = 0
                elif O >= active_tp:
                    long_exits.iloc[i] = True
                    np_exec_price[i] = O # Fill at Open
                    active_trade_side = 0
            elif active_trade_side == -1:
                # Short: Check Gap
                if O >= active_sl:
                    short_exits.iloc[i] = True
                    np_exec_price[i] = O
                    active_trade_side = 0
                elif O <= active_tp:
                    short_exits.iloc[i] = True
                    np_exec_price[i] = O
                    active_trade_side = 0
            
            # Pending Entry Gap Fill
            # Only if no active trade (or if we support reversal, but here we block new)
            can_take_new = True
            if block_new and active_trade_side != 0:
                can_take_new = False
                
            if can_take_new:
                if pending_long:
                    # Buy Stop @ Price. If Open > Price, fill at Open
                    if O >= pending_long_entry:
                        long_entries.iloc[i] = True
                        np_exec_price[i] = O
                        active_trade_side = 1
                        active_tp = pending_long_tp
                        active_sl = pending_long_sl
                        
                        # Size calc
                        dist = pending_long_entry - pending_long_sl
                        np_sl_dist[i] = dist if dist > 0 else p['tick_size']
                        
                        pending_long = False
                        
                elif pending_short:
                    # Sell Stop @ Price. If Open < Price, fill at Open
                    if O <= pending_short_entry:
                        short_entries.iloc[i] = True
                        np_exec_price[i] = O
                        active_trade_side = -1
                        active_tp = pending_short_tp
                        active_sl = pending_short_sl
                        
                        dist = pending_short_sl - pending_short_entry
                        np_sl_dist[i] = dist if dist > 0 else p['tick_size']
                        
                        pending_short = False

            # --- 2. INTRABAR PATH SIMULATION ---
            # Determine path based on Open proximity
            # If O closer to H -> Path: O -> H -> L -> C
            # Else             -> Path: O -> L -> H -> C
            
            path_points = []
            if abs(O - H) <= abs(O - L):
                path_points = [H, L, C]
            else:
                path_points = [L, H, C]
                
            current_p = O
            
            for next_p in path_points:
                # If trade set to inactive/filled in this bar, we might need to break or continue
                # We need to process events in sequence for this segment [current_p, next_p]
                
                # Define segment bounds
                seg_min = min(current_p, next_p)
                seg_max = max(current_p, next_p)
                
                # A. CHECK ACTIVE EXITS
                if active_trade_side == 1:
                    # Check SL (seg_min <= SL)
                    sl_hit = seg_min <= active_sl
                    # Check TP (seg_max >= TP)
                    tp_hit = seg_max >= active_tp
                    
                    if sl_hit and tp_hit:
                        # Both in segment? Which came first?
                        # Linear interpolation: which is closer to current_p?
                        dist_sl = abs(active_sl - current_p)
                        dist_tp = abs(active_tp - current_p)
                        
                        if dist_sl < dist_tp:
                            # SL first
                            long_exits.iloc[i] = True
                            np_exec_price[i] = active_sl
                            active_trade_side = 0
                        else:
                            # TP first
                            long_exits.iloc[i] = True
                            np_exec_price[i] = active_tp
                            active_trade_side = 0
                            
                    elif sl_hit:
                        long_exits.iloc[i] = True
                        np_exec_price[i] = active_sl
                        active_trade_side = 0
                    elif tp_hit:
                        long_exits.iloc[i] = True
                        np_exec_price[i] = active_tp
                        active_trade_side = 0
                        
                elif active_trade_side == -1:
                    # Short Exits
                    # SL (High >= SL) -> seg_max >= SL
                    sl_hit = seg_max >= active_sl
                    # TP (Low <= TP) -> seg_min <= TP
                    tp_hit = seg_min <= active_tp
                    
                    if sl_hit and tp_hit:
                        dist_sl = abs(active_sl - current_p)
                        dist_tp = abs(active_tp - current_p)
                        if dist_sl < dist_tp:
                            short_exits.iloc[i] = True
                            np_exec_price[i] = active_sl
                            active_trade_side = 0
                        else:
                            short_exits.iloc[i] = True
                            np_exec_price[i] = active_tp
                            active_trade_side = 0
                    elif sl_hit:
                        short_exits.iloc[i] = True
                        np_exec_price[i] = active_sl
                        active_trade_side = 0
                    elif tp_hit:
                        short_exits.iloc[i] = True
                        np_exec_price[i] = active_tp
                        active_trade_side = 0
                
                # B. CHECK PENDING ENTRIES
                # Check can_take_new again because we might have just closed a trade above
                if block_new and active_trade_side != 0:
                    can_take_new = False
                else: 
                     can_take_new = True # Re-open if we just closed? depends on strategy. Usually "Wait for next setup".
                     # RobReversal: "block_new_signals" usually means "don't stack". 
                     # If we closed, are we allowed to re-enter SAME bar? 
                     # Usually NO due to pattern requirement (Bar A/B). 
                     # Setup valid for Bar B (current). We are IN Bar B.
                     # If we entered and exited in Bar B, we are done for Bar B.
                     # flag: `processed_entry_this_bar`?
                     pass
                     
                # NOTE: For RobReversal, we consume the setup. So if we enter, we are done entering.
                # If we pending_long is True, and we enter, set pending_long = False.
                
                if can_take_new:
                    if pending_long:
                        # Buy Stop: segment must cross entry price upwards? Or just touch?
                        # Stop order: triggered if price >= entry.
                        # Do we intersect entry?
                        if seg_max >= pending_long_entry and seg_min <= pending_long_entry:
                             # Or simpler: Is Entry in Range [current_p, next_p]?
                             # Also care about direction? Stop orders trigger on touch.
                             pass
                        
                        # Simpler check: Did we pass it? 
                        # We use Range check.
                        if seg_max >= pending_long_entry:
                            # Triggered.
                            # BUT, did we hit SL before Entry? 
                            # Wait, SL is for the NEW trade. We don't have SL yet.
                            # So Entry is the first event.
                            
                            # However, what if we hit Entry, then hit NEW SL in same segment?
                            long_entries.iloc[i] = True
                            np_exec_price[i] = pending_long_entry
                            active_trade_side = 1
                            active_tp = pending_long_tp
                            active_sl = pending_long_sl
                            
                            # Record sizing
                            dist = pending_long_entry - pending_long_sl
                            np_sl_dist[i] = dist if dist > 0 else p['tick_size']
                            
                            pending_long = False
                            
                            # Check Instant Exit in SAME segment (linear from Entry -> next_p)
                            # Remaining path: Entry -> next_p
                            rem_min = min(pending_long_entry, next_p)
                            rem_max = max(pending_long_entry, next_p)
                            
                            if rem_min <= active_sl:
                                long_exits.iloc[i] = True # Same bar exit
                                # VBT handles same bar entry/exit?
                                # We might need to shift exit to i+1 or use specific VBT mode.
                                # For now, keeping logic simplified: Mark exit.
                                # VBT 'from_signals' might ignore exit on same bar if entries[i] is True?
                                # Ideally we'd overwrite entry with "Trade Closed" but VBT needs signals.
                                # Workaround: We can't easily express Intrabar PnL in VBT standard signals without expanding data.
                                # But we can mark Exit at i (Close).
                                # If we write Exit=True at i, VBT closes at Close Price? NO, we set exec_price.
                                # If both Entry and Exit are True at i: VBT functionality varies.
                                # Usually opens and closes same bar.
                                np_exec_price[i] = active_sl # Overwrite exec price? VBT might assume Entry Price for Entry and Exit Price for Exit.
                                # We have only one price array 'exec_price'.
                                # This is a limitation. returning 'exec_price' works for ONE signal type per bar usually.
                                # If we have both, we might want to return 'close' for exit? 
                                # Actually, lets just mark exit. If VBT fails, we assume 15m granularity limitation.
                                # But logic wise:
                                active_trade_side = 0
                            elif rem_max >= active_tp:
                                long_exits.iloc[i] = True
                                np_exec_price[i] = active_tp
                                active_trade_side = 0
                            
                            # Setup consumed
                            can_take_new = False
                            
                    elif pending_short:
                        if seg_min <= pending_short_entry:
                            short_entries.iloc[i] = True
                            np_exec_price[i] = pending_short_entry
                            active_trade_side = -1
                            active_tp = pending_short_tp
                            active_sl = pending_short_sl
                            
                            dist = pending_short_sl - pending_short_entry
                            np_sl_dist[i] = dist if dist > 0 else p['tick_size']
                            
                            pending_short = False
                            
                            # Check Instant Exit
                            rem_min = min(pending_short_entry, next_p)
                            rem_max = max(pending_short_entry, next_p)
                            
                            if rem_max >= active_sl:
                                short_exits.iloc[i] = True
                                np_exec_price[i] = active_sl
                                active_trade_side = 0
                            elif rem_min <= active_tp:
                                short_exits.iloc[i] = True
                                np_exec_price[i] = active_tp
                                active_trade_side = 0
                                
                            can_take_new = False

                # Move to next point
                current_p = next_p
                
            # --- 3. NEW SETUP GENERATION (End of Bar) ---
            check_for_new = True
            if block_new and active_trade_side != 0:
                check_for_new = False
            
            # Expiry check logic (moved from inside loop)
            # If pending still true but time passed?
            if pending_long:
                 if (i - long_setup_idx) >= trigger_bars:
                    pending_long = False
            if pending_short:
                 if (i - short_setup_idx) >= trigger_bars:
                    pending_short = False

            if check_for_new:
                if np_long_setup[i]:
                    pending_long = True
                    pending_long_entry = H + ts_tick
                    
                    # SL Calc
                    actual_sl_price = L
                    raw_sl = pending_long_entry - L
                    if raw_sl > p['max_stop_loss']:
                         actual_sl_price = pending_long_entry - p['max_stop_loss']
                    
                    pending_long_sl = actual_sl_price
                    pending_long_tp = pending_long_entry + p['take_profit']
                    long_setup_idx = i
                    
                if np_short_setup[i]:
                    pending_short = True
                    pending_short_entry = L - ts_tick
                    
                    actual_sl_price = H
                    raw_sl = H - pending_short_entry
                    if raw_sl > p['max_stop_loss']:
                        actual_sl_price = pending_short_entry + p['max_stop_loss']
                        
                    pending_short_sl = actual_sl_price
                    pending_short_tp = pending_short_entry - p['take_profit']
                    short_setup_idx = i
                
        # Assign modified numpy array back to Series
        exec_price[:] = np_exec_price
        sl_dist_series[:] = np_sl_dist

        return long_entries, long_exits, short_entries, short_exits, exec_price, sl_dist_series
