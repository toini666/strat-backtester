from .base import Strategy
import pandas as pd
import numpy as np

from typing import Tuple, Dict, Any

class VwapEmaStrategy(Strategy):
    """
    VWAP Reversal & EMA Trend Following Strategy.
    Based on Pine Script VWAP V2.

    Logic:
    - Setup: Price crosses VWAP.
    - Trigger: Retest of VWAP within tolerance.
    - Entry: Close of Trigger Bar because ball appears on NEXT candle.
    - Stop Loss: Lowest Low of last 4 bars (at Entry).
    - Exit: SL Hit or EMA Crossover (if armed).
    """

    name = "VwapEmaStrategy"

    default_params = {
        "ema_length": 8,
        "retest_tolerance": 0.3, 
        "max_setup_bars": 10,
        "trading_start_hour": 3,
        "trading_end_hour": 22,
        "utc_offset": 1,
        "tick_size": 0.25, # MNQ/NQ tick
        "sl_lookback": 4 # Bars for SL calc
    }

    def generate_signals(
        self,
        data: pd.DataFrame,
        params: Dict[str, Any] = None
    ) -> Tuple[pd.Series, pd.Series, pd.Series, pd.Series, pd.Series, pd.Series]:
        p = self.get_params(params)

        close = data['Close']
        low = data['Low']
        high = data['High']
        open_ = data['Open']
        
        # 1. Indicators
        if 'Volume' not in data.columns:
             raise ValueError("Volume data required for VWAP Strategy")

        # Standard VWAP Calculation anchored to Session Start (Midnight Local Time)
        # User is UTC+1. "Day" starts at 00:00 Local.
        
        utc_off = p.get('utc_offset', 1)
        offset = pd.Timedelta(hours=utc_off)
        
        # Shift index to Local Time
        local_time = data.index + offset
        
        # Group by "Day" (00:00 Local)
        day_groups = local_time.normalize()
        
        # Typical Price
        hlc3 = (high + low + close) / 3.0
        pv = hlc3 * data['Volume']
        
        # Cumulative Sums per Group
        cum_pv = pv.groupby(day_groups).cumsum()
        cum_vol = data['Volume'].groupby(day_groups).cumsum()
        
        vwap = cum_pv / cum_vol
        
        # Cleanup
        vwap = vwap.replace([np.inf, -np.inf], np.nan).fillna(method='ffill')

        # EMA (Native Pandas)
        ema = close.ewm(span=p['ema_length'], adjust=False).mean()
        
        sl_lb = int(p['sl_lookback'])
        lowest_sl = low.rolling(sl_lb).min()
        highest_sl = high.rolling(sl_lb).max()
        
        long_entries = pd.Series(False, index=data.index)
        long_exits = pd.Series(False, index=data.index)
        short_entries = pd.Series(False, index=data.index)
        short_exits = pd.Series(False, index=data.index)
        
        exec_price = close.copy() 
        sl_dist_series = pd.Series(np.nan, index=data.index)

        # Numpy Access
        np_close = close.values
        np_low = low.values
        np_high = high.values
        np_vwap = vwap.fillna(0).values 
        np_ema = ema.fillna(0).values
        np_lowest_sl = lowest_sl.values
        np_highest_sl = highest_sl.values
        np_index = data.index

        # Params
        tol = p['retest_tolerance']
        max_setup_bars = p['max_setup_bars']
        start_h = p['trading_start_hour']
        end_h = p['trading_end_hour']
        utc_off = p['utc_offset'] 
        tick_size = p['tick_size']

        def round_to_tick(price):
            return round(price / tick_size) * tick_size if tick_size > 0 else price

        # State Variables
        in_setup = False
        setup_is_long = False
        setup_bars = 0
        
        in_position = False
        is_long = False
        entry_price = 0.0
        stop_loss = 0.0
        ema_armed = False
        
        n = len(data)

        for i in range(1, n):
            curr_time = np_index[i]
            local_hour = (curr_time.hour + utc_off) % 24
            in_session = start_h <= local_hour < end_h

            prev_close = np_close[i-1]
            curr_close = np_close[i]
            curr_low = np_low[i]
            curr_high = np_high[i]
            
            prev_vwap = np_vwap[i-1]
            curr_vwap = np_vwap[i]
            curr_ema = np_ema[i]

            # --- 1. ENTRY SIGNAL (Check Pre-existing Setup) ---
            if in_setup and not in_position and in_session:
                triggered = False
                
                if setup_is_long:
                    # Retest Long: Low <= VWAP + Tol AND Close > VWAP
                    if (curr_low <= (curr_vwap + tol)) and (curr_close > curr_vwap):
                        long_entries.iloc[i] = True
                        in_position = True
                        is_long = True
                        entry_price = round_to_tick(curr_close)
                        stop_loss = round_to_tick(np_lowest_sl[i])
                        sl_dist_series.iloc[i] = entry_price - stop_loss
                        
                        # Arming Logic
                        ema_armed = (curr_close > curr_ema)
                        triggered = True
                        
                else: # Setup Short
                    # Retest Short: High >= VWAP - Tol AND Close < VWAP
                    if (curr_high >= (curr_vwap - tol)) and (curr_close < curr_vwap):
                        short_entries.iloc[i] = True
                        in_position = True
                        is_long = False
                        entry_price = round_to_tick(curr_close)
                        stop_loss = round_to_tick(np_highest_sl[i])
                        sl_dist_series.iloc[i] = stop_loss - entry_price

                        ema_armed = (curr_close < curr_ema)
                        triggered = True
                
                if triggered:
                    in_setup = False
                    setup_bars = 0
                    continue # Skip exit logic on entry bar matches Pine `bar_index > entryBar` logic
            
            # --- 2. EXIT LOGIC ---
            if in_position:
                exit_signal = False
                exit_p = 0.0
                
                if is_long:
                    # SL Check (Hit Low)
                    if curr_low <= stop_loss:
                        long_exits.iloc[i] = True
                        exit_p = stop_loss 
                        exit_signal = True
                    else:
                        # EMA Exit
                        if not ema_armed and curr_close > curr_ema:
                            ema_armed = True
                        if ema_armed and curr_close < curr_ema:
                            long_exits.iloc[i] = True
                            exit_p = round_to_tick(curr_close)
                            exit_signal = True
                else: # Short
                    if curr_high >= stop_loss:
                        short_exits.iloc[i] = True
                        exit_p = stop_loss
                        exit_signal = True
                    else:
                        # EMA Exit
                        if not ema_armed and curr_close < curr_ema:
                            ema_armed = True
                        if ema_armed and curr_close > curr_ema:
                            short_exits.iloc[i] = True
                            exit_p = round_to_tick(curr_close)
                            exit_signal = True
                
                if exit_signal:
                    in_position = False
                    exec_price.iloc[i] = exit_p
                    ema_armed = False
                    
                    # Check for Immediate Re-Entry / New Setup on Exit Bar
                    # Exit Cross Long: Prev < VWAP, Curr > VWAP
                    exit_cross_long = (prev_close < prev_vwap) and (curr_close > curr_vwap)
                    exit_cross_short = (prev_close > prev_vwap) and (curr_close < curr_vwap)
                    
                    if exit_cross_long and in_session:
                        in_setup = True
                        setup_is_long = True
                        setup_bars = 0
                    elif exit_cross_short and in_session:
                        in_setup = True
                        setup_is_long = False
                        setup_bars = 0
                    else:
                        in_setup = False
                        setup_bars = 0

            # --- 3. NEW SETUP GENERATION (Updates State for NEXT bar) ---
            # If not in position (and didn't just exit - handled above), check setup
            if not in_position and in_session:
                setup_long_triggered = (prev_close < prev_vwap) and (curr_close > curr_vwap)
                setup_short_triggered = (prev_close > prev_vwap) and (curr_close < curr_vwap)
                
                if setup_long_triggered:
                    in_setup = True
                    setup_is_long = True
                    setup_bars = 0
                elif setup_short_triggered:
                    in_setup = True
                    setup_is_long = False
                    setup_bars = 0
                elif in_setup:
                    setup_bars += 1
                    if setup_bars >= max_setup_bars:
                        in_setup = False
                        setup_bars = 0

        return long_entries, long_exits, short_entries, short_exits, exec_price, sl_dist_series
