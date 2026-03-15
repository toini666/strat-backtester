from .base import Strategy
import pandas as pd
import numpy as np
import pandas_ta_classic as ta
from typing import Tuple, Dict, Any

class UTBotSTC(Strategy):
    """
    UTBot Strategy with STC Filter and Heikin Ashi option.
    Based on Pine Script: 'UTBot-STC Strategy'.

    Key differences from UTBotHeikin:
    - Uses STC oscillator as filter instead of RSI/EMA200/Ribbon
    - Fixed SL/TP levels (not trailing after partial)
    - SL based on signal candle high/low + ticks offset
    - TP based on risk/reward ratio

    IMPORTANT: In Pine Script, when useHeikinAshi=True:
    - ATR is calculated on REAL prices (ta.atr uses chart's H/L/C)
    - STC is calculated on REAL close prices
    - Only 'src' for trailing stop uses HA close via request.security()
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
        "partial_rr": 2.0,        # R:R for partial TP level
        "partial_pct": 0.5,       # Fraction to close at partial TP (0.0-1.0)
        "breakeven_rr": 1.0,      # R:R to trigger breakeven
        "ema_length": 9,          # EMA length for final TP exit
        "tick_size": 0.25
    }

    # Parameter ranges for optimization
    param_ranges = {
        # UTBot Settings
        "key_value": [0.5, 1.0, 1.5, 2.0, 2.5, 3.0],
        "atr_period": [7, 10, 14, 20],
        "use_heikin_ashi": [True, False],

        # STC Settings
        "stc_length": [8, 10, 12, 14, 16],
        "stc_fast_length": [20, 23, 26, 30],
        "stc_slow_length": [40, 50, 60],

        # STC Level Filters
        "stc_min_long": [1.0, 5.0, 10.0],
        "stc_max_long": [60.0, 70.0, 75.0, 80.0],
        "stc_min_short": [20.0, 25.0, 30.0, 40.0],
        "stc_max_short": [90.0, 95.0, 99.0],

        # Position Management
        "stop_ticks": [2, 3, 4, 5],
        "partial_rr": [1.5, 2.0, 2.5, 3.0],
        "partial_pct": [0.3, 0.5, 0.7],
        "breakeven_rr": [0.5, 1.0, 1.5],
        "ema_length": [5, 9, 13, 21],
    }

    def generate_signals(
        self,
        data: pd.DataFrame,
        params: Dict[str, Any] = None
    ) -> Tuple[pd.Series, pd.Series, pd.Series, pd.Series, pd.Series, pd.Series, pd.Series]:
        p = self.get_params(params)

        # Ensure we have enough data
        min_len = max(p['stc_slow_length'], p['atr_period'], p['ema_length']) + p['stc_length'] + 10
        if len(data) < min_len:
            empty = pd.Series(False, index=data.index)
            zeros = pd.Series(0.0, index=data.index)
            nans = pd.Series(np.nan, index=data.index)
            return empty, empty, empty, empty, zeros, nans, nans

        # REAL prices - always used for execution and structural levels (SL/TP)
        real_close = data['Close']
        real_open = data['Open']
        real_high = data['High']
        real_low = data['Low']

        # ===========================================
        # 1. Select Candle Source for Strategy Logic (Signals)
        # ===========================================
        # HYBRID LOGIC:
        # - ATR and STC always use REAL prices (Standard Chart).
        # - UTBot Signal Source (src) uses Heikin Ashi if enabled.
        
        # Default: Indicators use Real Prices
        calc_close = real_close
        calc_high = real_high
        calc_low = real_low
        
        if p['use_heikin_ashi']:
            ha_close = (real_open + real_high + real_low + real_close) / 4

            # HA Open requires iteration
            np_ha_open = np.zeros(len(data))
            np_ha_open[0] = real_open.values[0]
            np_ha_close = ha_close.values

            for i in range(1, len(data)):
                np_ha_open[i] = (np_ha_open[i-1] + np_ha_close[i-1]) / 2

            ha_open = pd.Series(np_ha_open, index=data.index)

            # HA High/Low (max/min of real H/L and HA O/C)
            ha_high = pd.DataFrame({'a': real_high, 'b': ha_open, 'c': ha_close}).max(axis=1)
            ha_low = pd.DataFrame({'a': real_low, 'b': ha_open, 'c': ha_close}).min(axis=1)

            # UTBot Source uses HA
            src = ha_close
        else:
            # UTBot Source uses Real
            src = real_close

        # ===========================================
        # 2. UTBot Trailing Stop Calculation
        # ===========================================
        # ATR uses REAL prices (calc_*) regardless of HA setting
        xATR = ta.atr(calc_high, calc_low, calc_close, length=p['atr_period'])
        nLoss = p['key_value'] * xATR

        np_src = src.values
        np_nLoss = nLoss.values
        np_trail = np.zeros(len(data))

        np_trail[0] = 0.0  # Pine uses nz(..., 0)

        for i in range(1, len(data)):
            prev_trail = np_trail[i-1]
            curr_src = np_src[i]
            prev_src = np_src[i-1]
            curr_nLoss = np_nLoss[i] if not np.isnan(np_nLoss[i]) else 0

            if (curr_src > prev_trail) and (prev_src > prev_trail):
                np_trail[i] = max(prev_trail, curr_src - curr_nLoss)
            elif (curr_src < prev_trail) and (prev_src < prev_trail):
                np_trail[i] = min(prev_trail, curr_src + curr_nLoss)
            elif curr_src > prev_trail:
                np_trail[i] = curr_src - curr_nLoss
            else:
                np_trail[i] = curr_src + curr_nLoss

        xATRTrailingStop = pd.Series(np_trail, index=data.index)

        # ===========================================
        # 3. UTBot Signal Generation
        # ===========================================
        prev_src = src.shift(1)
        prev_trail = xATRTrailingStop.shift(1)

        # Crossover detection using SIGNAL prices
        above = (src > xATRTrailingStop) & (prev_src <= prev_trail)
        below = (src < xATRTrailingStop) & (prev_src >= prev_trail)

        utbot_long = (src > xATRTrailingStop) & above
        utbot_short = (src < xATRTrailingStop) & below

        # ===========================================
        # 4. STC Calculation
        # ===========================================
        stc_len = p['stc_length']
        fast_len = p['stc_fast_length']
        slow_len = p['stc_slow_length']

        fast_ma = ta.ema(calc_close, length=fast_len)
        slow_ma = ta.ema(calc_close, length=slow_len)
        macd_val = fast_ma - slow_ma

        np_macd = macd_val.fillna(0).values

        macd_s = pd.Series(np_macd)
        low_macd = macd_s.rolling(window=stc_len, min_periods=stc_len).min().bfill().values
        high_macd = macd_s.rolling(window=stc_len, min_periods=stc_len).max().bfill().values

        pf_series = np.zeros(len(data))
        pff_prev = 0.0
        pf_prev = 0.0
        factor = 0.5

        for i in range(len(data)):
            m_val = np_macd[i]
            l_val = low_macd[i]
            h_val = high_macd[i]
            rng1 = h_val - l_val

            if rng1 > 0:
                pff = (m_val - l_val) / rng1 * 100
            else:
                pff = pff_prev

            pff_prev = pff
            pf = pf_prev + factor * (pff - pf_prev)
            pf_prev = pf
            pf_series[i] = pf

        pf_s = pd.Series(pf_series)
        low_pf = pf_s.rolling(window=stc_len, min_periods=stc_len).min().bfill().values
        high_pf = pf_s.rolling(window=stc_len, min_periods=stc_len).max().bfill().values

        stc_final = np.zeros(len(data))
        pfff_prev = 0.0
        pff2_prev = 0.0

        for i in range(len(data)):
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

        # ===========================================
        # 5. STC Filter Conditions
        # ===========================================
        stc_prev = stc_val.shift(1)

        stc_rising = stc_val > stc_prev
        stc_falling = stc_val < stc_prev

        stc_valid_long = (stc_val >= p['stc_min_long']) & (stc_val <= p['stc_max_long']) & stc_rising
        stc_valid_short = (stc_val >= p['stc_min_short']) & (stc_val <= p['stc_max_short']) & stc_falling

        # ===========================================
        # 6. Combined Entry Signals
        # ===========================================
        green_candle = real_close > real_open
        red_candle = real_close < real_open

        long_signal = utbot_long & stc_valid_long & green_candle
        short_signal = utbot_short & stc_valid_short & red_candle

        # ===========================================
        # 7. EMA for Final TP Exit
        # ===========================================
        ema_final = ta.ema(real_close, length=p['ema_length'])
        np_ema_final = ema_final.ffill().bfill().values

        # ===========================================
        # 8. Position Management — State Machine
        # ===========================================
        # Matching PineScript logic exactly:
        #   - Entry: close price, SL from candle low/high + ticks
        #   - Breakeven trigger at breakeven_rr
        #   - Partial TP at partial_rr (close partial_pct of position)
        #   - Final exit via EMA cross (only after partial taken)
        #   - SL exit at any time

        n = len(data)
        long_entries = pd.Series(False, index=data.index)
        long_exits = pd.Series(False, index=data.index)
        short_entries = pd.Series(False, index=data.index)
        short_exits = pd.Series(False, index=data.index)
        exec_prices = real_close.copy()
        sl_dists = pd.Series(np.nan, index=data.index)
        exit_ratios = pd.Series(1.0, index=data.index)

        # Helper for rounding
        tick_sz = p['tick_size'] if p['tick_size'] > 0 else 0.25
        def round_to_tick(price):
            return round(price / tick_sz) * tick_sz

        # Parameters
        stop_ticks = p['stop_ticks']
        partial_rr = p['partial_rr']
        partial_pct = p['partial_pct']
        breakeven_rr = p['breakeven_rr']

        np_long_sig = long_signal.values
        np_short_sig = short_signal.values

        # Pre-convert to numpy for speed (ffill+bfill to prevent NaN zombie positions)
        np_real_close = real_close.ffill().bfill().values
        np_real_high = real_high.ffill().bfill().values
        np_real_low = real_low.ffill().bfill().values

        # State variables (matching PineScript var declarations)
        in_pos = False
        pos_side = ""          # "LONG" or "SHORT"
        entry_price = 0.0
        stop_price = 0.0
        partial_tp_price = 0.0
        be_level_price = 0.0
        partial_taken = False
        breakeven_activated = False
        signal_bar = -1

        for i in range(1, n):
            # ===========================================
            # EVENT FLAGS (reset each bar, like PineScript)
            # ===========================================
            hit_partial_tp = False
            hit_stop = False
            hit_stop_be = False
            hit_final_tp_ema = False

            ev_entry_long = False
            ev_entry_short = False
            ev_partial_price = np.nan
            ev_close_price = np.nan

            # ===========================================
            # EXIT LOGIC (only after entry bar)
            # Pine: if inPosition and bar_index > signalBar
            # ===========================================
            if in_pos and i > signal_bar:

                if pos_side == "LONG":
                    curr_high = np_real_high[i]
                    curr_low = np_real_low[i]
                    curr_close = np_real_close[i]

                    # 1. Partial TP (once only)
                    if not partial_taken and curr_high >= partial_tp_price:
                        hit_partial_tp = True
                        partial_taken = True
                        ev_partial_price = partial_tp_price

                    # 2. Breakeven activation
                    if not breakeven_activated and curr_high >= be_level_price:
                        breakeven_activated = True
                        stop_price = entry_price  # Move SL to entry

                    # 3. Stop loss hit
                    if curr_low <= stop_price:
                        if breakeven_activated:
                            hit_stop_be = True
                        else:
                            hit_stop = True
                        ev_close_price = stop_price

                    # 4. Final TP via EMA (only after partial taken)
                    if partial_taken and curr_close < np_ema_final[i]:
                        hit_final_tp_ema = True
                        ev_close_price = round_to_tick(curr_close)

                    # Close position if any exit condition
                    if hit_stop or hit_stop_be or hit_final_tp_ema:
                        in_pos = False
                        signal_bar = -1

                elif pos_side == "SHORT":
                    curr_high = np_real_high[i]
                    curr_low = np_real_low[i]
                    curr_close = np_real_close[i]

                    # 1. Partial TP (once only)
                    if not partial_taken and curr_low <= partial_tp_price:
                        hit_partial_tp = True
                        partial_taken = True
                        ev_partial_price = partial_tp_price

                    # 2. Breakeven activation
                    if not breakeven_activated and curr_low <= be_level_price:
                        breakeven_activated = True
                        stop_price = entry_price  # Move SL to entry

                    # 3. Stop loss hit
                    if curr_high >= stop_price:
                        if breakeven_activated:
                            hit_stop_be = True
                        else:
                            hit_stop = True
                        ev_close_price = stop_price

                    # 4. Final TP via EMA (only after partial taken)
                    if partial_taken and curr_close > np_ema_final[i]:
                        hit_final_tp_ema = True
                        ev_close_price = round_to_tick(curr_close)

                    # Close position if any exit condition
                    if hit_stop or hit_stop_be or hit_final_tp_ema:
                        in_pos = False
                        signal_bar = -1

            # ===========================================
            # ENTRY LOGIC (only if not in position)
            # ===========================================
            if not in_pos:
                if np_long_sig[i]:
                    entry_p = round_to_tick(np_real_close[i])
                    sig_low = np_real_low[i]
                    stop_p = round_to_tick(sig_low - stop_ticks * tick_sz)
                    risk_amt = entry_p - stop_p

                    if risk_amt > 0:
                        ev_entry_long = True
                        in_pos = True
                        pos_side = "LONG"
                        signal_bar = i
                        entry_price = entry_p
                        stop_price = stop_p
                        partial_tp_price = round_to_tick(entry_p + risk_amt * partial_rr)
                        be_level_price = round_to_tick(entry_p + risk_amt * breakeven_rr)
                        partial_taken = False
                        breakeven_activated = False

                elif np_short_sig[i]:
                    entry_p = round_to_tick(np_real_close[i])
                    sig_high = np_real_high[i]
                    stop_p = round_to_tick(sig_high + stop_ticks * tick_sz)
                    risk_amt = stop_p - entry_p

                    if risk_amt > 0:
                        ev_entry_short = True
                        in_pos = True
                        pos_side = "SHORT"
                        signal_bar = i
                        entry_price = entry_p
                        stop_price = stop_p
                        partial_tp_price = round_to_tick(entry_p - risk_amt * partial_rr)
                        be_level_price = round_to_tick(entry_p - risk_amt * breakeven_rr)
                        partial_taken = False
                        breakeven_activated = False

            # ===========================================
            # RECORD SIGNALS
            # ===========================================

            # ENTRIES
            if ev_entry_long:
                long_entries.iloc[i] = True
                exec_prices.iloc[i] = entry_price
                sl_dists.iloc[i] = entry_price - stop_price

            if ev_entry_short:
                short_entries.iloc[i] = True
                exec_prices.iloc[i] = entry_price
                sl_dists.iloc[i] = stop_price - entry_price

            # PARTIAL EXITS (TP1)
            if hit_partial_tp and pos_side == "LONG":
                long_exits.iloc[i] = True
                exec_prices.iloc[i] = ev_partial_price
                exit_ratios.iloc[i] = partial_pct

            if hit_partial_tp and pos_side == "SHORT":
                short_exits.iloc[i] = True
                exec_prices.iloc[i] = ev_partial_price
                exit_ratios.iloc[i] = partial_pct

            # FULL EXITS (SL, BE, EMA)
            if hit_stop or hit_stop_be or hit_final_tp_ema:
                if not np.isnan(ev_close_price):
                    # pos_side is still the side of the closed trade
                    if pos_side == "LONG":
                        long_exits.iloc[i] = True
                        exec_prices.iloc[i] = ev_close_price
                        exit_ratios.iloc[i] = 1.0
                    elif pos_side == "SHORT":
                        short_exits.iloc[i] = True
                        exec_prices.iloc[i] = ev_close_price
                        exit_ratios.iloc[i] = 1.0

        return long_entries, long_exits, short_entries, short_exits, exec_prices, sl_dists, exit_ratios
