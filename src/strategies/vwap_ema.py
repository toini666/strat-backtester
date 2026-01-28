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
        "retest_tolerance": 1.0,  # Match PineScript default (was 0.3)
        "max_setup_bars": 10,
        "trading_start_hour": 3,
        "trading_end_hour": 22,
        "utc_offset": 1,
        "tick_size": 0.25,  # MNQ/NQ tick
        "sl_lookback": 4  # Bars for SL calc
    }

    # Parameter ranges for optimization
    param_ranges = {
        "ema_length": [5, 8, 10, 13, 20],
        "retest_tolerance": [0.5, 0.75, 1.0, 1.5, 2.0],
        "max_setup_bars": [5, 8, 10, 15],
        "sl_lookback": [3, 4, 5, 6],
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

        # VWAP Calculation anchored to Session Start (Midnight Local Time)
        # IMPORTANT: PineScript ta.vwap(close) uses CLOSE as source, not hlc3!
        # User is UTC+1. "Day" starts at 00:00 Local.

        utc_off = p.get('utc_offset', 1)
        offset = pd.Timedelta(hours=utc_off)

        # Shift index to Local Time
        local_time = data.index + offset

        # Group by "Day" (00:00 Local)
        day_groups = local_time.normalize()

        # Use CLOSE as source (matches PineScript: ta.vwap(close))
        pv = close * data['Volume']

        # Cumulative Sums per Group
        cum_pv = pv.groupby(day_groups).cumsum()
        cum_vol = data['Volume'].groupby(day_groups).cumsum()

        vwap = cum_pv / cum_vol

        # Cleanup
        vwap = vwap.replace([np.inf, -np.inf], np.nan).ffill()

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

        # Track entry bar to skip exit logic on entry bar (Pine: bar_index > entryBar)
        entry_bar = -1

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

            # ============================================
            # PINE FLOW ORDER (must match exactly):
            # In PineScript, var variables retain their value from the PREVIOUS bar.
            # So when evaluating longSignal = inSetup and ..., inSetup has its
            # value from BEFORE any modifications on this bar.
            #
            # Flow:
            # 1. Increment setupBarCount if in setup (uses previous bar's state)
            # 2. Timeout setup if exceeded
            # 3. Calculate entry signals FIRST (using PREVIOUS bar's setup state)
            # 4. Create NEW setups (updates state for NEXT bar)
            # 5. Process entries (using signals calculated at step 3)
            # 6. Handle exits
            # ============================================

            # --- 1. INCREMENT SETUP COUNTER (uses state from previous bar) ---
            if in_setup and not in_position:
                setup_bars += 1

            # --- 2. TIMEOUT CHECK ---
            if in_setup and not in_position and setup_bars >= max_setup_bars:
                in_setup = False
                setup_bars = 0

            # --- 3. CALCULATE ENTRY SIGNALS FIRST (before new setup creation!) ---
            # This is crucial: signals must use the setup state from PREVIOUS bar
            # Retest conditions
            retest_long_vwap = (curr_low <= (curr_vwap + tol)) and (curr_close > curr_vwap)
            retest_short_vwap = (curr_high >= (curr_vwap - tol)) and (curr_close < curr_vwap)

            # Signal: setup active (from previous bar) AND retest valid
            long_signal = in_setup and setup_is_long and in_session and retest_long_vwap
            short_signal = in_setup and (not setup_is_long) and in_session and retest_short_vwap

            # --- 4. NEW SETUP DETECTION (updates state for next bar) ---
            # Setup: VWAP crossover detection
            setup_long_triggered = (not in_position and in_session and
                                    prev_close < prev_vwap and curr_close > curr_vwap)
            setup_short_triggered = (not in_position and in_session and
                                     prev_close > prev_vwap and curr_close < curr_vwap)

            if setup_long_triggered:
                in_setup = True
                setup_is_long = True
                setup_bars = 0  # Reset counter on new setup

            if setup_short_triggered:
                in_setup = True
                setup_is_long = False
                setup_bars = 0  # Reset counter on new setup

            # --- 5. PROCESS ENTRIES (using signals calculated BEFORE setup update) ---
            if long_signal and not in_position:
                long_entries.iloc[i] = True
                in_position = True
                is_long = True
                entry_price = round_to_tick(curr_close)
                stop_loss = round_to_tick(np_lowest_sl[i])
                sl_dist_series.iloc[i] = entry_price - stop_loss
                entry_bar = i

                # Arm EMA exit
                ema_armed = (curr_close > curr_ema)

                # Clear setup state
                in_setup = False
                setup_bars = 0

            elif short_signal and not in_position:
                short_entries.iloc[i] = True
                in_position = True
                is_long = False
                entry_price = round_to_tick(curr_close)
                stop_loss = round_to_tick(np_highest_sl[i])
                sl_dist_series.iloc[i] = stop_loss - entry_price
                entry_bar = i

                # Arm EMA exit
                ema_armed = (curr_close < curr_ema)

                # Clear setup state
                in_setup = False
                setup_bars = 0

            # --- 5. EXIT LOGIC (only after entry bar, matching Pine: bar_index > entryBar) ---
            if in_position and i > entry_bar:
                exit_signal = False
                exit_p = 0.0

                if is_long:
                    # SL Check
                    if curr_low <= stop_loss:
                        long_exits.iloc[i] = True
                        exit_p = stop_loss
                        exit_signal = True
                    else:
                        # EMA Exit (arm then trigger)
                        if not ema_armed and curr_close > curr_ema:
                            ema_armed = True
                        if ema_armed and curr_close < curr_ema:
                            long_exits.iloc[i] = True
                            exit_p = round_to_tick(curr_close)
                            exit_signal = True
                else:  # Short
                    if curr_high >= stop_loss:
                        short_exits.iloc[i] = True
                        exit_p = stop_loss
                        exit_signal = True
                    else:
                        # EMA Exit (arm then trigger)
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
                    entry_bar = -1

                    # Check for immediate new setup on exit bar (Pine behavior)
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

        return long_entries, long_exits, short_entries, short_exits, exec_price, sl_dist_series
