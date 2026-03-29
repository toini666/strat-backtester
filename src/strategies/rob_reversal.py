"""
Rob Reversal strategy.

Translated from PineScript indicator RobReversal.txt.
Pattern: price sweeps a previous bar's extreme and reverses back inside its body,
filtered by EMA direction and a multi-filter oscillator (4Kings + Smart Money Flow).

Setup (Bar A = previous bar, Bar B = current bar):
  Long : barA bearish, barB sweeps barA low, barB closes back into barA body, close > EMA
  Short: barA bullish, barB sweeps barA high, barB closes back into barA body, close < EMA

Entry: stop-entry order placed at barB_high+tick (long) or barB_low-tick (short).
       Triggered when price touches that level within the next `trigger_bars` bars.
       Entry price = the stop-entry level (not bar close).

Exit: single fixed TP (min of RR-based and points-based), single SL (barB extreme,
      capped by max_stop_loss points). No partial TPs. Auto-close handled by simulator.

Oscillator filters (all independently togglable):
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
from collections import deque
from typing import Dict, Any

import warnings

try:
    import pandas_ta_classic as ta
except ImportError:
    import pandas_ta as ta

warnings.filterwarnings("ignore", category=FutureWarning)


class RobReversal(Strategy):
    """Rob Reversal — sweep-and-reverse with 4Kings + MFI oscillator filters."""

    name = "RobReversal"
    manual_exit = True
    use_simulator = True
    blackout_sensitive = True
    simulator_settings = {
        "tp1_execution_mode": "touch",   # immediate exit on TP touch (matches Pine)
        "tp1_full_exit": True,           # single TP, close 100% of position
    }

    default_params = {
        # EMA filter
        "ema_length": 13,

        # Strategy
        "take_profit": 40.0,     # fixed TP in points
        "risk_reward": 2.0,      # RR ratio (TP = min of fixed vs RR-based)
        "max_stop_loss": 40.0,   # maximum SL distance in points
        "trigger_bars": 2,       # bars after setup to watch for trigger

        # 4Kings Oscillator
        "hyper_wave_length": 5,
        "signal_type": "SMA",    # "SMA" or "EMA"
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
        "ema_length": [9, 13, 21],
        "take_profit": [30.0, 40.0, 50.0, 60.0],
        "risk_reward": [1.5, 2.0, 2.5, 3.0],
        "max_stop_loss": [30.0, 40.0, 50.0],
        "trigger_bars": [1, 2, 3],
        "hyper_wave_length": [3, 5, 7],
        "signal_length": [2, 3, 4],
        "mf_length": [25, 30, 35, 40],
        "hw_extreme": [15.0, 20.0, 25.0],
        "hw_range": [7.0, 10.0, 13.0],
    }

    # ------------------------------------------------------------------
    # Oscillator helpers (identical logic to EMABreakOsc)
    # ------------------------------------------------------------------

    @staticmethod
    def _compute_oscillator(close, high, low, hl2, mL, sT, sL):
        """4Kings Oscillator — returns (osc_sig, osc_sgd) Series."""
        hi = high.rolling(window=mL).max()
        lo = low.rolling(window=mL).min()
        av = hl2.rolling(window=mL).mean()
        avg_hla = (hi + lo + av) / 3
        raw_osc = (close - avg_hla) / (hi - lo + 1e-10) * 100

        # Linear regression endpoint (ta.linreg equivalent)
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
        Identical implementation to EMABreakOsc._compute_mfi_cloud.

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
    # Signal generation
    # ------------------------------------------------------------------

    def generate_signals(self, data: pd.DataFrame, params: Dict[str, Any] = None) -> Dict[str, Any]:
        p = self.get_params(params)

        ema_len     = p["ema_length"]
        tp_points   = p["take_profit"]
        rr          = p["risk_reward"]
        max_sl      = p["max_stop_loss"]
        trig_bars   = p["trigger_bars"]
        mL          = p["hyper_wave_length"]
        sT          = p["signal_type"]
        sL          = p["signal_length"]
        mfL         = p["mf_length"]
        mfS         = p["mf_smooth"]
        tick        = p["tick_size"]

        # Filter flags
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
        is_blackout = (
            data["is_blackout"].fillna(False).astype(bool).values
            if "is_blackout" in data.columns
            else np.zeros(len(data), dtype=bool)
        )
        volume = data["Volume"]
        hl2    = (high + low) / 2

        n = len(data)

        # ---- Vectorised indicators ----
        ema_main = close.ewm(span=ema_len, adjust=False).mean()
        osc_sig, osc_sgd = self._compute_oscillator(close, high, low, hl2, mL, sT, sL)
        mfi = self._compute_mfi(hl2, volume, mfL, mfS)

        mfi_vals = mfi.values.copy()
        cloud_long_arr, cloud_short_arr, _, cloud_line_arr = self._compute_mfi_cloud(mfi_vals, mfL)

        np_close = close.values
        np_open  = open_.values
        np_high  = high.values
        np_low   = low.values
        np_ema   = ema_main.values
        np_osc   = osc_sig.values
        np_sgd   = osc_sgd.values

        def round_tick(price):
            return round(price / tick) * tick if tick > 0 else price

        # ---- Output arrays ----
        long_entries      = np.zeros(n, dtype=bool)
        short_entries     = np.zeros(n, dtype=bool)
        sl_long_arr       = np.full(n, np.nan)
        sl_short_arr      = np.full(n, np.nan)
        tp1_long_arr      = np.full(n, np.nan)
        tp1_short_arr     = np.full(n, np.nan)
        entry_price_long  = np.full(n, np.nan)
        entry_price_short = np.full(n, np.nan)

        # ---- Stateful variables ----
        last_confirmed_hw     = 0       # 1 = last cross was bullish, -1 = bearish
        last_confirmed_hw_val = np.nan  # osc value at last cross

        # Pending order state
        pending_long_order  = False
        pending_long_entry  = np.nan
        pending_long_sl     = np.nan
        pending_long_tp     = np.nan
        long_setup_bar_idx  = -9999

        pending_short_order  = False
        pending_short_entry  = np.nan
        pending_short_sl     = np.nan
        pending_short_tp     = np.nan
        short_setup_bar_idx  = -9999

        delta_long_on_prev  = False
        delta_short_on_prev = False

        start_bar = max(ema_len, mfL + mfS, mL + sL) + 5

        for i in range(start_bar, n):
            c  = np_close[i]
            o  = np_open[i]
            h  = np_high[i]
            lo = np_low[i]

            c_prev = np_close[i - 1]
            o_prev = np_open[i - 1]
            h_prev = np_high[i - 1]
            l_prev = np_low[i - 1]

            ema_i = np_ema[i]
            if np.isnan(ema_i):
                continue

            sig_i    = np_osc[i]   if not np.isnan(np_osc[i])  else 0.0
            sgd_i    = np_sgd[i]   if not np.isnan(np_sgd[i])  else 0.0
            sig_prev = np_osc[i-1] if i > 0 and not np.isnan(np_osc[i-1]) else 0.0
            sgd_prev = np_sgd[i-1] if i > 0 and not np.isnan(np_sgd[i-1]) else 0.0
            mfi_i    = cloud_line_arr[i] if not np.isnan(cloud_line_arr[i]) else 0.0

            # ---- ① HW crossover / crossunder detection ----
            hw_cross_over  = sig_prev <= sgd_prev and sig_i > sgd_i
            hw_cross_under = sig_prev >= sgd_prev and sig_i < sgd_i

            if hw_cross_over:
                last_confirmed_hw     = 1
                last_confirmed_hw_val = min(sig_i, sgd_i)
            if hw_cross_under:
                last_confirmed_hw     = -1
                last_confirmed_hw_val = max(sig_i, sgd_i)

            # ---- Delta states (current bar) ----
            delta_long_on  = sig_i > 0 and mfi_i > 0
            delta_short_on = sig_i < 0 and mfi_i < 0

            # ---- 8 oscillator filter conditions ----
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

            # ⑤ Nuage MFI
            cloud_long_ok_i  = bool(cloud_long_arr[i])
            cloud_short_ok_i = bool(cloud_short_arr[i])

            # ⑤+⑥ combined gate (OR)
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

            # ---- Check trigger window ----
            bars_since_long  = i - long_setup_bar_idx
            bars_since_short = i - short_setup_bar_idx

            in_long_trigger  = pending_long_order  and 1 <= bars_since_long  <= trig_bars
            in_short_trigger = pending_short_order and 1 <= bars_since_short <= trig_bars

            long_triggered  = in_long_trigger  and h >= pending_long_entry and not is_blackout[i]
            short_triggered = in_short_trigger and lo <= pending_short_entry and not is_blackout[i]

            entered_this_bar = False

            if long_triggered:
                long_entries[i]      = True
                entry_price_long[i]  = pending_long_entry
                sl_long_arr[i]       = pending_long_sl
                tp1_long_arr[i]      = pending_long_tp
                # Cancel both pending orders
                pending_long_order  = False
                pending_short_order = False
                entered_this_bar = True

            elif short_triggered:
                short_entries[i]      = True
                entry_price_short[i]  = pending_short_entry
                sl_short_arr[i]       = pending_short_sl
                tp1_short_arr[i]      = pending_short_tp
                pending_short_order = False
                pending_long_order  = False
                entered_this_bar = True

            # Cancel expired pending orders
            if pending_long_order and bars_since_long > trig_bars:
                pending_long_order = False
            if pending_short_order and bars_since_short > trig_bars:
                pending_short_order = False

            # ---- Detect new setups (Rob Reversal pattern) ----
            # Bar A = previous bar [i-1], Bar B = current bar [i]
            barA_is_bearish = c_prev < o_prev
            barA_is_bullish = c_prev > o_prev
            barA_body_high = max(o_prev, c_prev)
            barA_body_low  = min(o_prev, c_prev)

            long_setup_raw = (
                barA_is_bearish and
                lo < l_prev - tick and              # sweep barA low
                c > barA_body_low and c < barA_body_high and  # close inside barA body
                c > ema_i                           # above EMA filter
            )
            short_setup_raw = (
                barA_is_bullish and
                h > h_prev + tick and               # sweep barA high
                c < barA_body_high and c > barA_body_low and  # close inside barA body
                c < ema_i                           # below EMA filter
            )

            long_setup  = long_setup_raw  and osc_all_long_ok
            short_setup = short_setup_raw and osc_all_short_ok

            # Store pending orders (only if we didn't just enter this bar)
            if long_setup and not entered_this_bar:
                entry_l = round_tick(h + tick)          # barB_high + 1 tick
                raw_sl  = entry_l - lo
                sl_l    = entry_l - max_sl if raw_sl > max_sl else lo
                sl_dist = entry_l - sl_l
                tp_rr   = entry_l + sl_dist * rr
                tp_pts  = entry_l + tp_points
                pending_long_entry  = entry_l
                pending_long_sl     = sl_l
                pending_long_tp     = min(tp_rr, tp_pts)
                pending_long_order  = True
                long_setup_bar_idx  = i

            if short_setup and not entered_this_bar:
                entry_s = round_tick(lo - tick)         # barB_low - 1 tick
                raw_sl  = h - entry_s
                sl_s    = entry_s + max_sl if raw_sl > max_sl else h
                sl_dist = sl_s - entry_s
                tp_rr   = entry_s - sl_dist * rr
                tp_pts  = entry_s - tp_points
                pending_short_entry  = entry_s
                pending_short_sl     = sl_s
                pending_short_tp     = max(tp_rr, tp_pts)
                pending_short_order  = True
                short_setup_bar_idx  = i

            # Advance delta state for next bar
            delta_long_on_prev  = delta_long_on
            delta_short_on_prev = delta_short_on

        # ---- Build debug frame ----
        debug_df = pd.DataFrame({
            "ema_main":   np_ema,
            "osc_sig":    np_osc,
            "osc_sgd":    np_sgd,
            "mfi":        mfi_vals,
            "is_blackout": is_blackout.astype(int),
        }, index=data.index)

        return {
            "long_entries":         pd.Series(long_entries,      index=data.index),
            "short_entries":        pd.Series(short_entries,     index=data.index),
            "sl_long":              pd.Series(sl_long_arr,       index=data.index),
            "sl_short":             pd.Series(sl_short_arr,      index=data.index),
            "tp1_long":             pd.Series(tp1_long_arr,      index=data.index),
            "tp1_short":            pd.Series(tp1_short_arr,     index=data.index),
            "entry_price_long":     pd.Series(entry_price_long,  index=data.index),
            "entry_price_short":    pd.Series(entry_price_short, index=data.index),
            # EMA cross exit disabled — pass NaN so the simulator skips it entirely
            "ema_main":             pd.Series(np.nan, index=data.index),
            "ema_secondary":        pd.Series(np.nan, index=data.index),
            "debug_frame":          debug_df,
        }
