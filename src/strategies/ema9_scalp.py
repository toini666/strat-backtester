"""
EMA9 Momentum Retest (Scalp) strategy — simulator-based.

Translated from PineScript indicator EMA9-scalp.txt.
Uses a state machine for setup detection, retest confirmation, and breakout entry.

Entry: N consecutive bullish/bearish candles above/below EMA with first candle
       touching EMA, then price retests EMA within tolerance, then breakout
       above previous high (long) or below previous low (short).
Exit: Stop loss, TP1 partial (RR-based or fixed points, at bar close when touched),
      breakeven at separate BE level, EMA cross exit after TP1.

Oscillator filters (all independently togglable, same logic as RobReversal):
  ① hwDir      — last HW crossover direction must match trade direction
  ② hwExtreme  — |value at last HW cross| ≤ hw_extreme
  ③ sigExtreme — |current osc_sig| ≤ hw_extreme
  ④ hwRange    — |value at last HW cross| > hw_range (not in flat zone)
  ⑤ cloud      — MFI cloud side matches trade direction (or delta fallback ⑥)
  ⑥ delta      — delta short not active for longs; delta long not active for shorts
  ⑦ cloudZero  — MFI value sign matches direction (< 0 for long, > 0 for short)
  ⑧ deltaExt   — opposite delta just extinguished (transition from active→inactive)
"""

from .base import Strategy
import pandas as pd
import numpy as np
import pandas_ta_classic as ta
from collections import deque
from typing import Dict, Any


class EMA9Scalp(Strategy):
    """EMA9 Momentum Retest — scalp entries on EMA retest breakout."""

    name = "EMA9Scalp"
    manual_exit = True
    use_simulator = True
    simulator_settings = {
        "tp1_execution_mode": "bar_close_if_touched",
        "ema_exit_after_tp1_only": True,
    }

    default_params = {
        # Indicator
        "ema_length": 7,

        # Setup
        "nb_candles": 3,
        "setup_bar_can_retest": False,
        "retest_tolerance": 1,       # ticks
        "max_bars": 10,

        # Position / Risk
        "sl_margin": 3,              # ticks
        "max_stop_points": 60.0,     # max SL distance in points
        "rr_be": 1.0,               # R:R to move SL to breakeven
        "rr_tp1": 2.0,              # R:R for TP1
        "tp1_points": 50.0,         # fixed TP1 distance in points (0 = disabled)
        "tp1_partial_pct": 0.50,    # 50% of position closed at TP1
        "tp2_partial_pct": 0.0,     # no TP2

        # 4Kings Oscillator
        "hyper_wave_length": 5,
        "signal_type": "SMA",       # "SMA" or "EMA"
        "signal_length": 3,

        # Smart Money Flow
        "mf_length": 35,
        "mf_smooth": 6,

        # Oscillator filters (toggleable)
        "hw_dir_on": True,
        "hw_extreme_on": True,
        "hw_extreme": 20.0,
        "sig_extreme_on": True,
        "hw_range_on": True,
        "hw_range": 10.0,
        "cloud_on": True,
        "delta_on": True,
        "cloud_zero_on": True,
        "delta_ext_on": True,

        # Injected by engine
        "tick_size": 0.25,
    }

    param_ranges = {
        "ema_length": [5, 7, 9, 13],
        "nb_candles": [2, 3, 4, 5],
        "retest_tolerance": [0, 1, 2, 3],
        "max_bars": [5, 10, 15, 20],
        "sl_margin": [0, 2, 3, 5],
        "max_stop_points": [30.0, 40.0, 50.0, 60.0],
        "rr_be": [0.5, 1.0, 1.5],
        "rr_tp1": [1.5, 2.0, 2.5, 3.0],
        "tp1_points": [0.0, 30.0, 50.0, 70.0],
        "tp1_partial_pct": [0.3, 0.5, 0.7],
        "hyper_wave_length": [3, 5, 7],
        "signal_length": [2, 3, 4],
        "mf_length": [25, 30, 35, 40],
        "hw_extreme": [15.0, 20.0, 25.0],
        "hw_range": [7.0, 10.0, 13.0],
    }

    # ------------------------------------------------------------------
    # Oscillator helpers (identical logic to RobReversal / EMABreakOsc)
    # ------------------------------------------------------------------

    @staticmethod
    def _compute_oscillator(close, high, low, hl2, mL, sT, sL):
        """4Kings Oscillator — returns (osc_sig, osc_sgd) Series."""
        hi = high.rolling(window=mL).max()
        lo = low.rolling(window=mL).min()
        av = hl2.rolling(window=mL).mean()
        avg_hla = (hi + lo + av) / 3
        raw_osc = (close - avg_hla) / (hi - lo + 1e-10) * 100

        osc_linreg = pd.Series(np.nan, index=close.index)
        np_raw = raw_osc.values
        for i in range(mL - 1, len(close)):
            window = np_raw[i - mL + 1: i + 1]
            if not np.any(np.isnan(window)):
                x = np.arange(mL)
                try:
                    coeffs = np.polyfit(x, window, 1)
                    osc_linreg.iloc[i] = coeffs[0] * (mL - 1) + coeffs[1]
                except Exception:
                    osc_linreg.iloc[i] = window[-1]

        osc_sig = osc_linreg.ewm(span=sL, adjust=False).mean()
        osc_sgd = (
            osc_sig.rolling(2).mean() if sT == "SMA"
            else osc_sig.ewm(span=2, adjust=False).mean()
        )
        return osc_sig, osc_sgd

    @staticmethod
    def _compute_mfi(hl2, volume, mfL, mfS):
        """Smart Money Flow Index centred at 0, matching Pine's ta.mfi(hl2)."""
        tp = hl2
        raw_mf = tp * volume
        tp_change = tp.diff()

        pos_flow = raw_mf.where(tp_change > 0, 0.0)
        neg_flow = raw_mf.where(tp_change < 0, 0.0)

        pos_sum = pos_flow.rolling(window=mfL).sum()
        neg_sum = neg_flow.rolling(window=mfL).sum()

        ratio = pos_sum / (neg_sum + 1e-10)
        mfi_raw = 100 - (100 / (1 + ratio))
        return mfi_raw.rolling(window=mfS).mean() - 50

    @staticmethod
    def _compute_mfi_cloud(mfi_values, mfL):
        """
        Pine blT / brT array tracking for MFI cloud reference line.
        Returns (cloud_long, cloud_short, ref_line_arr, cloud_line_arr).
        """
        n = len(mfi_values)
        cloud_long = np.zeros(n, dtype=bool)
        cloud_short = np.zeros(n, dtype=bool)
        ref_line_arr = np.full(n, np.nan)
        cloud_line_arr = np.full(n, np.nan)

        blT = deque([np.nan])
        brT = deque([np.nan])

        def _avg(arr):
            valid = [v for v in arr if not np.isnan(v)]
            return np.mean(valid) if valid else np.nan

        for i in range(n):
            m = mfi_values[i]
            if np.isnan(m):
                continue

            hist_m = mfi_values[i - mfL] if i >= mfL and not np.isnan(mfi_values[i - mfL]) else np.nan

            if m > 0:
                if len(brT) > 1:
                    brT.pop()
                if len(blT) > mfL:
                    blT.pop()
                bl_avg = _avg(blT)
                if not np.isnan(bl_avg) and m > bl_avg:
                    blT.appendleft(m)
                else:
                    val = hist_m if (not np.isnan(hist_m) and hist_m > 0) else m
                    blT.appendleft(val)
            elif m < 0:
                if len(blT) > 1:
                    blT.pop()
                if len(brT) > mfL:
                    brT.pop()
                bl_avg = _avg(blT)
                if not np.isnan(bl_avg) and m < bl_avg:
                    brT.appendleft(m)
                else:
                    val = hist_m if (not np.isnan(hist_m) and hist_m < 0) else m
                    brT.appendleft(val)

            if m > 0:
                ref = _avg(blT)
            elif m < 0:
                ref = _avg(brT)
            else:
                ref = np.nan

            ref_line_arr[i] = ref
            cloud_line_arr[i] = m
            if not np.isnan(ref) and m != 0:
                cloud_long[i] = ref < m
                cloud_short[i] = ref > m

        return cloud_long, cloud_short, ref_line_arr, cloud_line_arr

    # ------------------------------------------------------------------

    def get_simulator_settings(self, params=None):
        p = self.get_params(params)
        settings = self.simulator_settings.copy()
        settings["tp1_partial_pct"] = p.get("tp1_partial_pct", 0.50)
        settings["tp2_partial_pct"] = p.get("tp2_partial_pct", 0.0)
        return settings

    # ------------------------------------------------------------------
    # Main signal generation
    # ------------------------------------------------------------------

    def generate_signals(
        self, data: pd.DataFrame, params: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Run the full PineScript state machine to detect entries.

        The state machine tracks both setup/entry states (0,1,2,5,6) and
        position states (3,4,7,8,9,10) at the bar level. This ensures
        entry timing matches PineScript exactly — setups are blocked while
        a position is active, just as in TradingView.

        The simulator then re-executes position management with intra-bar
        resolution for more accurate exit pricing.
        """
        p = self.get_params(params)

        ema_len = p["ema_length"]
        nb_candles = p["nb_candles"]
        setup_bar_can_retest = p["setup_bar_can_retest"]
        retest_tol_ticks = p["retest_tolerance"]
        max_bars = p["max_bars"]
        sl_margin = p["sl_margin"]
        max_stop_pts = p["max_stop_points"]
        rr_be = p["rr_be"]
        rr_tp1 = p["rr_tp1"]
        tp1_points = p["tp1_points"]
        tick_size = p["tick_size"]

        mL  = p["hyper_wave_length"]
        sT  = p["signal_type"]
        sL  = p["signal_length"]
        mfL = p["mf_length"]
        mfS = p["mf_smooth"]

        hw_dir_on      = p["hw_dir_on"]
        hw_extreme_on  = p["hw_extreme_on"]
        hw_extreme     = p["hw_extreme"]
        sig_extreme_on = p["sig_extreme_on"]
        hw_range_on    = p["hw_range_on"]
        hw_range       = p["hw_range"]
        cloud_on       = p["cloud_on"]
        delta_on       = p["delta_on"]
        cloud_zero_on  = p["cloud_zero_on"]
        delta_ext_on   = p["delta_ext_on"]

        close  = data["Close"]
        open_  = data["Open"]
        high   = data["High"]
        low    = data["Low"]
        volume = data["Volume"]
        hl2    = (high + low) / 2
        n = len(data)

        # --- EMA ---
        ema = ta.ema(close, length=ema_len)

        # --- Oscillator ---
        osc_sig, osc_sgd = self._compute_oscillator(close, high, low, hl2, mL, sT, sL)
        mfi = self._compute_mfi(hl2, volume, mfL, mfS)
        mfi_vals = mfi.values.copy()
        cloud_long_arr, cloud_short_arr, _, cloud_line_arr = self._compute_mfi_cloud(mfi_vals, mfL)

        # --- Numpy arrays ---
        np_close = close.values
        np_open = open_.values
        np_high = high.values
        np_low = low.values
        np_ema = ema.values
        np_osc = osc_sig.values
        np_sgd = osc_sgd.values

        tol_price = retest_tol_ticks * tick_size

        def round_tick(price):
            if tick_size > 0:
                return round(price / tick_size) * tick_size
            return price

        def get_tp1_long(entry, risk):
            rr_target = entry + risk * rr_tp1
            if tp1_points > 0:
                fixed_target = entry + tp1_points
                return round_tick(min(rr_target, fixed_target))
            return round_tick(rr_target)

        def get_tp1_short(entry, risk):
            rr_target = entry - risk * rr_tp1
            if tp1_points > 0:
                fixed_target = entry - tp1_points
                return round_tick(max(rr_target, fixed_target))
            return round_tick(rr_target)

        # --- Output arrays ---
        long_entries = np.zeros(n, dtype=bool)
        short_entries = np.zeros(n, dtype=bool)
        sl_long_arr = np.full(n, np.nan)
        sl_short_arr = np.full(n, np.nan)
        tp1_long_arr = np.full(n, np.nan)
        tp1_short_arr = np.full(n, np.nan)
        be_long_arr = np.full(n, np.nan)
        be_short_arr = np.full(n, np.nan)

        # --- Debug arrays ---
        state_arr = np.zeros(n, dtype=int)

        # --- State machine ---
        trade_state = 0
        setup_bar = -1
        ready_bar = -1  # bar where retest confirmed (for entry delay)
        entry_bar = -1
        # Position tracking at bar level (mirrors PineScript for entry blocking)
        entry_price = np.nan
        sl_price = np.nan
        tp1_price = np.nan
        be_level = np.nan

        # --- Oscillator stateful variables ---
        last_confirmed_hw     = 0       # 1 = last HW cross was bullish, -1 = bearish
        last_confirmed_hw_val = np.nan  # osc value at last cross
        delta_long_on_prev    = False
        delta_short_on_prev   = False

        start_bar = max(ema_len + 2, nb_candles + 1, mfL + mfS + mL + sL + 5)

        for i in range(start_bar, n):
            if np.isnan(np_ema[i]):
                state_arr[i] = trade_state
                continue

            # ============================================
            # OSCILLATOR STATE (computed every bar)
            # ============================================
            sig_i    = np_osc[i]     if not np.isnan(np_osc[i])   else 0.0
            sgd_i    = np_sgd[i]     if not np.isnan(np_sgd[i])   else 0.0
            sig_prev = np_osc[i - 1] if not np.isnan(np_osc[i-1]) else 0.0
            sgd_prev = np_sgd[i - 1] if not np.isnan(np_sgd[i-1]) else 0.0
            mfi_i    = cloud_line_arr[i] if not np.isnan(cloud_line_arr[i]) else 0.0

            hw_cross_over  = sig_prev <= sgd_prev and sig_i > sgd_i
            hw_cross_under = sig_prev >= sgd_prev and sig_i < sgd_i

            if hw_cross_over:
                last_confirmed_hw     = 1
                last_confirmed_hw_val = min(sig_i, sgd_i)
            if hw_cross_under:
                last_confirmed_hw     = -1
                last_confirmed_hw_val = max(sig_i, sgd_i)

            delta_long_on  = sig_i > 0 and mfi_i > 0
            delta_short_on = sig_i < 0 and mfi_i < 0

            # ① Sens HW
            hw_dir_long_ok  = not hw_dir_on or last_confirmed_hw == 1
            hw_dir_short_ok = not hw_dir_on or last_confirmed_hw == -1

            # ② Extrêmes HW (value at last cross)
            hw_extreme_long_ok  = not hw_extreme_on or np.isnan(last_confirmed_hw_val) or last_confirmed_hw_val <= hw_extreme
            hw_extreme_short_ok = not hw_extreme_on or np.isnan(last_confirmed_hw_val) or last_confirmed_hw_val >= -hw_extreme

            # ③ Extrêmes SIG courant
            sig_extreme_long_ok  = not sig_extreme_on or sig_i <= hw_extreme
            sig_extreme_short_ok = not sig_extreme_on or sig_i >= -hw_extreme

            # ④ Range HW
            hw_range_ok = not hw_range_on or np.isnan(last_confirmed_hw_val) or abs(last_confirmed_hw_val) > hw_range

            # ⑤+⑥ Nuage MFI + delta (OR)
            cloud_long_ok_i  = bool(cloud_long_arr[i])
            cloud_short_ok_i = bool(cloud_short_arr[i])
            cloud_or_delta_long_ok  = not cloud_on or cloud_long_ok_i  or (delta_on and delta_long_on)
            cloud_or_delta_short_ok = not cloud_on or cloud_short_ok_i or (delta_on and delta_short_on)

            # ⑥ Deltas
            delta_long_ok  = not delta_on or not delta_short_on
            delta_short_ok = not delta_on or not delta_long_on

            # ⑦ Nuage < 0 / > 0
            cloud_zero_long_ok  = not cloud_zero_on or mfi_i < 0
            cloud_zero_short_ok = not cloud_zero_on or mfi_i > 0

            # ⑧ Extinction deltas
            delta_ext_long_ok  = not delta_ext_on or (delta_short_on_prev and not delta_short_on)
            delta_ext_short_ok = not delta_ext_on or (delta_long_on_prev  and not delta_long_on)

            osc_all_long_ok  = (hw_dir_long_ok  and hw_extreme_long_ok  and sig_extreme_long_ok
                                and hw_range_ok and cloud_or_delta_long_ok  and delta_long_ok
                                and cloud_zero_long_ok  and delta_ext_long_ok)
            osc_all_short_ok = (hw_dir_short_ok and hw_extreme_short_ok and sig_extreme_short_ok
                                and hw_range_ok and cloud_or_delta_short_ok and delta_short_ok
                                and cloud_zero_short_ok and delta_ext_short_ok)

            # ============================================
            # SETUP DETECTION (computed every bar)
            # ============================================
            # Long setup: N consecutive bullish candles closing above EMA
            long_setup_ok = True
            for k in range(nb_candles):
                idx = i - k
                if idx < 0 or np.isnan(np_ema[idx]):
                    long_setup_ok = False
                    break
                if not (np_close[idx] > np_open[idx] and np_close[idx] > np_ema[idx]):
                    long_setup_ok = False
                    break

            if long_setup_ok:
                first_idx = i - (nb_candles - 1)
                long_first_touch = np_low[first_idx] <= np_ema[first_idx]
                long_confirm_touch = (
                    setup_bar_can_retest
                    and np_low[i] <= np_ema[i] + tol_price
                )
                long_setup_ok = long_first_touch or long_confirm_touch
            else:
                long_first_touch = False
                long_confirm_touch = False

            # Short setup: N consecutive bearish candles closing below EMA
            short_setup_ok = True
            for k in range(nb_candles):
                idx = i - k
                if idx < 0 or np.isnan(np_ema[idx]):
                    short_setup_ok = False
                    break
                if not (np_close[idx] < np_open[idx] and np_close[idx] < np_ema[idx]):
                    short_setup_ok = False
                    break

            if short_setup_ok:
                first_idx = i - (nb_candles - 1)
                short_first_touch = np_high[first_idx] >= np_ema[first_idx]
                short_confirm_touch = (
                    setup_bar_can_retest
                    and np_high[i] >= np_ema[i] - tol_price
                )
                short_setup_ok = short_first_touch or short_confirm_touch
            else:
                short_first_touch = False
                short_confirm_touch = False

            # ============================================
            # BLOC 1: STATE MACHINE — SETUP / RETEST
            # ============================================
            if trade_state == 0:
                if long_setup_ok:
                    retest_already_done = long_confirm_touch
                    trade_state = 2 if retest_already_done else 1
                    setup_bar = i
                    ready_bar = i if retest_already_done else -1
                elif short_setup_ok:
                    retest_already_done = short_confirm_touch
                    trade_state = 6 if retest_already_done else 5
                    setup_bar = i
                    ready_bar = i if retest_already_done else -1

            elif trade_state == 1:  # SETUP LONG — waiting for retest
                if i - setup_bar >= max_bars:
                    trade_state = 0
                    ready_bar = -1
                elif np_low[i] <= np_ema[i] + tol_price:
                    if np_close[i] > np_ema[i]:
                        trade_state = 2
                        ready_bar = i
                    else:
                        trade_state = 0
                        ready_bar = -1

            elif trade_state == 2:  # READY LONG — waiting for breakout
                if i - setup_bar >= max_bars:
                    trade_state = 0
                    ready_bar = -1
                elif np_close[i] < np_ema[i]:
                    trade_state = 0
                    ready_bar = -1

            elif trade_state == 5:  # SETUP SHORT — waiting for retest
                if i - setup_bar >= max_bars:
                    trade_state = 0
                    ready_bar = -1
                elif np_high[i] >= np_ema[i] - tol_price:
                    if np_close[i] < np_ema[i]:
                        trade_state = 6
                        ready_bar = i
                    else:
                        trade_state = 0
                        ready_bar = -1

            elif trade_state == 6:  # READY SHORT — waiting for breakout
                if i - setup_bar >= max_bars:
                    trade_state = 0
                    ready_bar = -1
                elif np_close[i] > np_ema[i]:
                    trade_state = 0
                    ready_bar = -1

            # ============================================
            # BLOC 2: ENTRY CHECKS (from READY states)
            # ============================================
            # PineScript: canAct = bar_index > lastActionBar
            # We use: i > ready_bar (no entry on the readyBar itself)
            can_enter_long = (
                trade_state == 2
                and (ready_bar < 0 or i > ready_bar)
                and i > entry_bar  # not on same bar as previous entry
            )
            if can_enter_long:
                long_break_trigger = round_tick(np_high[i - 1] + tick_size)
                if np_high[i] >= long_break_trigger and np_close[i] >= np_ema[i] and osc_all_long_ok:
                    actual_entry = round_tick(np_close[i])
                    raw_sl = round_tick(np_low[i - 1] - sl_margin * tick_size)
                    raw_risk = actual_entry - raw_sl
                    actual_risk = min(raw_risk, max_stop_pts)
                    actual_sl = round_tick(actual_entry - actual_risk)

                    if actual_risk > 0:
                        entry_price = actual_entry
                        sl_price = actual_sl
                        tp1_price = get_tp1_long(actual_entry, actual_risk)
                        be_level = round_tick(actual_entry + actual_risk * rr_be)
                        entry_bar = i

                        long_entries[i] = True
                        sl_long_arr[i] = actual_sl
                        tp1_long_arr[i] = tp1_price
                        be_long_arr[i] = be_level

                        trade_state = 3  # LONG FULL (position active)

            can_enter_short = (
                trade_state == 6
                and (ready_bar < 0 or i > ready_bar)
                and i > entry_bar
            )
            if can_enter_short:
                short_break_trigger = round_tick(np_low[i - 1] - tick_size)
                if np_low[i] <= short_break_trigger and np_close[i] <= np_ema[i] and osc_all_short_ok:
                    actual_entry = round_tick(np_close[i])
                    raw_sl = round_tick(np_high[i - 1] + sl_margin * tick_size)
                    raw_risk = raw_sl - actual_entry
                    actual_risk = min(raw_risk, max_stop_pts)
                    actual_sl = round_tick(actual_entry + actual_risk)

                    if actual_risk > 0:
                        entry_price = actual_entry
                        sl_price = actual_sl
                        tp1_price = get_tp1_short(actual_entry, actual_risk)
                        be_level = round_tick(actual_entry - actual_risk * rr_be)
                        entry_bar = i

                        short_entries[i] = True
                        sl_short_arr[i] = actual_sl
                        tp1_short_arr[i] = tp1_price
                        be_short_arr[i] = be_level

                        trade_state = 7  # SHORT FULL (position active)

            # ============================================
            # BLOC 3: BAR-LEVEL POSITION MANAGEMENT
            # (mirrors PineScript for state tracking only —
            #  actual execution is handled by the simulator)
            # ============================================
            if i > entry_bar:
                # --- LONG FULL (state 3) ---
                if trade_state == 3:
                    if np_low[i] <= sl_price:
                        trade_state = 0
                    elif np_high[i] >= tp1_price:
                        sl_price = entry_price
                        trade_state = 4  # LONG PARTIAL
                    elif np_high[i] >= be_level:
                        sl_price = entry_price
                        trade_state = 9  # LONG BE

                # --- LONG BE (state 9) ---
                elif trade_state == 9:
                    if np_low[i] <= sl_price:
                        trade_state = 0
                    elif np_high[i] >= tp1_price:
                        trade_state = 4  # LONG PARTIAL

                # --- LONG PARTIAL (state 4) ---
                elif trade_state == 4:
                    if np_low[i] <= sl_price:
                        trade_state = 0
                    elif np_close[i] < np_ema[i]:
                        trade_state = 0

                # --- SHORT FULL (state 7) ---
                elif trade_state == 7:
                    if np_high[i] >= sl_price:
                        trade_state = 0
                    elif np_low[i] <= tp1_price:
                        sl_price = entry_price
                        trade_state = 8  # SHORT PARTIAL
                    elif np_low[i] <= be_level:
                        sl_price = entry_price
                        trade_state = 10  # SHORT BE

                # --- SHORT BE (state 10) ---
                elif trade_state == 10:
                    if np_high[i] >= sl_price:
                        trade_state = 0
                    elif np_low[i] <= tp1_price:
                        trade_state = 8  # SHORT PARTIAL

                # --- SHORT PARTIAL (state 8) ---
                elif trade_state == 8:
                    if np_high[i] >= sl_price:
                        trade_state = 0
                    elif np_close[i] > np_ema[i]:
                        trade_state = 0

            # Advance delta state for next bar
            delta_long_on_prev  = delta_long_on
            delta_short_on_prev = delta_short_on

            state_arr[i] = trade_state

        # --- Build output ---
        debug_frame = pd.DataFrame(
            {
                "Open": open_,
                "High": high,
                "Low": low,
                "Close": close,
                "ema": ema,
                "osc_sig": osc_sig,
                "osc_sgd": osc_sgd,
                "mfi": mfi,
                "state": state_arr,
                "long_entry_signal": long_entries.astype(int),
                "short_entry_signal": short_entries.astype(int),
                "sl_long": sl_long_arr,
                "sl_short": sl_short_arr,
                "tp1_long": tp1_long_arr,
                "tp1_short": tp1_short_arr,
                "be_long": be_long_arr,
                "be_short": be_short_arr,
            },
            index=data.index,
        )

        return {
            "long_entries": pd.Series(long_entries, index=data.index),
            "short_entries": pd.Series(short_entries, index=data.index),
            "sl_long": pd.Series(sl_long_arr, index=data.index),
            "sl_short": pd.Series(sl_short_arr, index=data.index),
            "tp1_long": pd.Series(tp1_long_arr, index=data.index),
            "tp1_short": pd.Series(tp1_short_arr, index=data.index),
            "be_long": pd.Series(be_long_arr, index=data.index),
            "be_short": pd.Series(be_short_arr, index=data.index),
            "ema_main": ema,
            "ema_secondary": ema,  # same EMA, no TP2
            "cooldown_bars": 0,
            "debug_frame": debug_frame,
        }
