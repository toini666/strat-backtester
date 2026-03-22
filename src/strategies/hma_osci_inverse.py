"""
HMA Oscillator Inverse strategy.

Translated from PineScript indicator HMA-Osci-Inverse.txt.
Uses the same indicators as HMAOsci (HMA Ribbon + 4Kings Oscillator + Smart Money Flow)
but takes the OPPOSITE position to the original signal:

  Original LONG  conditions → enter SHORT (invShortEntry)
  Original SHORT conditions → enter LONG  (invLongEntry)

SL / TP are swapped relative to the original:
  Inverse SHORT: TP = original SL long  = min(low, canalLower)  [below entry]
                 SL = entry + min(risk × RR, tp_points)          [above entry]
  Inverse LONG:  TP = original SL short = max(high, canalUpper) [above entry]
                 SL = entry - min(risk × RR, tp_points)          [below entry]

Position sizing uses the TP distance (= original SL distance) as the risk reference,
matching how the normal HMAOsci indicator sizes positions.

Exit logic (no partials — all exits close 100% of the position):
  1. SL touch  → full close at SL price (intrabar)
  2. TP touch  → full close at TP price (intrabar)
  3. Canal exit at bar close:
       Inverse SHORT: close < canalLower
       Inverse LONG:  close > canalUpper
  4. Auto-close at configured time
"""

from .hma_osci import HMAOsci
import pandas as pd
import numpy as np
from typing import Dict, Any


class HMAOsciInverse(HMAOsci):
    """HMA Oscillator Inverse — enters counter to the original HMAOsci signal."""

    name = "HMAOsciInverse"
    manual_exit = True
    use_simulator = True
    simulator_settings = {
        # TP fires intrabar (touch), closes full position — no partial
        "tp1_execution_mode": "touch",
        "tp1_full_exit": True,
        "tp1_partial_pct": 0.0,
        "tp2_partial_pct": 0.0,
        # Canal exit is inverted: LONG exits when close > upper, SHORT exits when close < lower
        "inverse_canal_exit": True,
    }

    default_params = {
        # HMA Ribbon — different defaults from original (Inverse uses faster/shorter HMA)
        "ema_len": 10,
        "hma1_len": 13,
        "hma2_len": 21,
        "amp_mult": 2.0,

        # 4Kings Oscillator (same as original)
        "hyper_wave_length": 5,
        "signal_type": "SMA",
        "signal_length": 3,

        # Smart Money Flow (same as original)
        "mf_length": 35,
        "mf_smooth": 6,

        # Filters
        "hw_filter_on": True,
        "hw_extreme": 20.0,
        "hw_range_filter_on": False,
        "hw_range": 16.0,
        # In the inverse, this is the max TP distance (= original SL distance)
        "max_sl_points": 20.0,
        "cooldown_bars": 1,
        "max_candle_pct": 0.3,

        # Risk Management
        "tick_buffer": 0,       # Buffer ticks applied to TP (= original SL level)
        # RR ratio used to compute the inverse SL: SL = entry ± min(risk × rr_partial, tp_points)
        "rr_partial": 2.0,
        # Fixed-points cap on the SL distance: SL = entry ± min(risk × rr_partial, tp_points)
        "tp_points": 20.0,

        # Injected by engine
        "tick_size": 0.25,
    }

    param_ranges = {
        "ema_len": [7, 10, 13],
        "hma1_len": [10, 13, 17],
        "hma2_len": [17, 21, 28],
        "amp_mult": [1.5, 2.0, 2.5],
        "hyper_wave_length": [3, 5, 7],
        "signal_length": [2, 3, 4],
        "mf_length": [25, 30, 35, 40],
        "mf_smooth": [4, 6, 8],
        "hw_extreme": [15.0, 20.0, 25.0],
        "hw_range": [10.0, 14.0, 16.0, 20.0],
        "max_sl_points": [15.0, 20.0, 25.0, 30.0],
        "cooldown_bars": [0, 1, 2],
        "max_candle_pct": [0.2, 0.3, 0.4],
        "rr_partial": [1.5, 2.0, 2.5, 3.0],
        "tp_points": [15.0, 20.0, 25.0],
    }

    def get_simulator_settings(self, params=None):
        # No partial pcts — always full exit at TP1
        return self.simulator_settings.copy()

    def generate_signals(
        self, data: pd.DataFrame, params: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        p = self.get_params(params)

        ema_len = p["ema_len"]
        hma1_len = p["hma1_len"]
        hma2_len = p["hma2_len"]
        amp_mult = p["amp_mult"]
        mL = p["hyper_wave_length"]
        sT = p["signal_type"]
        sL = p["signal_length"]
        mfL = p["mf_length"]
        mfS = p["mf_smooth"]
        hw_filter_on = p["hw_filter_on"]
        hw_extreme = p["hw_extreme"]
        hw_range_filter_on = p["hw_range_filter_on"]
        hw_range = p["hw_range"]
        max_tp_points = p["max_sl_points"]   # in inverse: max TP distance
        max_candle_pct = p["max_candle_pct"]
        tick_buf = p["tick_buffer"]
        rr_partial = p["rr_partial"]
        tp_points = p["tp_points"]
        tick_size = p["tick_size"]

        close = data["Close"]
        open_ = data["Open"]
        high = data["High"]
        low = data["Low"]
        volume = data["Volume"]
        hl2 = (high + low) / 2

        n = len(data)

        # --- Indicators (reuse parent class static methods) ---
        src_ema, canal_upper_s, canal_lower_s, canal_green_s = self._compute_hma_canal(
            close, ema_len, hma1_len, hma2_len, amp_mult
        )
        osc_sig, osc_sgd = self._compute_oscillator(close, high, low, hl2, mL, sT, sL)
        mfi = self._compute_mfi(hl2, volume, mfL, mfS)

        mfi_vals = mfi.values.copy()
        cloud_long_arr, cloud_short_arr, cloud_ref_arr, cloud_line_arr = (
            self._compute_mfi_cloud(mfi_vals, mfL)
        )

        # --- Numpy arrays ---
        np_close = close.values
        np_open = open_.values
        np_high = high.values
        np_low = low.values
        np_canal_upper = canal_upper_s.values
        np_canal_lower = canal_lower_s.values
        np_canal_green = canal_green_s.values
        np_osc = osc_sig.values if osc_sig is not None else np.full(n, np.nan)
        np_sgd = osc_sgd.values if osc_sgd is not None else np.full(n, np.nan)
        np_mfi = mfi_vals

        def _safe(v):
            return 0.0 if np.isnan(v) else v

        def candle_pct(o, c):
            if c == 0:
                return 999.0
            return abs(c - o) / c * 100.0

        def round_tick(price):
            if tick_size > 0:
                return round(price / tick_size) * tick_size
            return price

        # --- Output arrays ---
        long_entries = np.zeros(n, dtype=bool)
        short_entries = np.zeros(n, dtype=bool)
        sl_long_arr = np.full(n, np.nan)
        sl_short_arr = np.full(n, np.nan)
        tp1_long_arr = np.full(n, np.nan)
        tp1_short_arr = np.full(n, np.nan)
        # Size-risk prices: TP levels used for position sizing (= original SL levels)
        size_risk_long_arr = np.full(n, np.nan)
        size_risk_short_arr = np.full(n, np.nan)

        # --- Debug arrays ---
        last_confirmed_hw_arr = np.full(n, np.nan)
        last_confirmed_hw_val_arr = np.full(n, np.nan)
        delta_long_arr = np.zeros(n, dtype=bool)
        delta_short_arr = np.zeros(n, dtype=bool)
        hma_break_long_arr = np.zeros(n, dtype=bool)
        hma_break_short_arr = np.zeros(n, dtype=bool)
        candle_ok_arr = np.zeros(n, dtype=bool)

        # --- Stateful tracking ---
        last_confirmed_hw = 0
        last_confirmed_hw_val = np.nan

        import math
        start_bar = max(
            ema_len * 4 + hma2_len + int(math.sqrt(hma2_len)),
            mfL + mfS,
            mL + sL,
        ) + 10

        for i in range(start_bar, n):
            c = np_close[i]
            o = np_open[i]
            hi = np_high[i]
            lo = np_low[i]
            cu = np_canal_upper[i]
            cl = np_canal_lower[i]
            cg = np_canal_green[i]

            if np.isnan(cu) or np.isnan(cl):
                continue

            sig_i = _safe(np_osc[i])
            sgd_i = _safe(np_sgd[i])
            sig_p = _safe(np_osc[i - 1]) if i > 0 else 0.0
            sgd_p = _safe(np_sgd[i - 1]) if i > 0 else 0.0
            mfi_i = _safe(np_mfi[i])

            # --- HW crossover/crossunder ---
            hw_cross_over = sig_p <= sgd_p and sig_i > sgd_i
            hw_cross_under = sig_p >= sgd_p and sig_i < sgd_i

            if hw_cross_over:
                last_confirmed_hw = 1
                last_confirmed_hw_val = min(sig_i, sgd_i)
            if hw_cross_under:
                last_confirmed_hw = -1
                last_confirmed_hw_val = max(sig_i, sgd_i)

            # --- Delta states ---
            delta_long_on = sig_i > 0 and mfi_i > 0
            delta_short_on = sig_i < 0 and mfi_i < 0
            delta_long_arr[i] = delta_long_on
            delta_short_arr[i] = delta_short_on

            # --- Candle size filter ---
            cpct = candle_pct(o, c)
            candle_ok = cpct <= max_candle_pct
            candle_ok_arr[i] = candle_ok

            # --- HMA break signals (identical to original — conditions, not entries) ---
            hma_break_long = bool(cg) and c > cu and candle_ok   # original long condition
            hma_break_short = not bool(cg) and c < cl and candle_ok  # original short condition
            hma_break_long_arr[i] = hma_break_long
            hma_break_short_arr[i] = hma_break_short

            # --- HW extreme filter ---
            if np.isnan(last_confirmed_hw_val):
                hw_long_allowed = True
                hw_short_allowed = True
                hw_range_ok = True
            else:
                hw_long_allowed = (not hw_filter_on) or (last_confirmed_hw_val <= hw_extreme)
                hw_short_allowed = (not hw_filter_on) or (last_confirmed_hw_val >= -hw_extreme)
                hw_range_ok = (not hw_range_filter_on) or (abs(last_confirmed_hw_val) > hw_range)

            # --- Cloud filter ---
            cloud_long_ok = cloud_long_arr[i]
            cloud_short_ok = cloud_short_arr[i]

            # --- TP levels (= original SL levels) ---
            # Inverse SHORT TP = original long SL = min(low, canalLower) - tick_buffer
            raw_tp_inv_short = min(lo, cl) - tick_buf * tick_size
            # Inverse LONG  TP = original short SL = max(high, canalUpper) + tick_buffer
            raw_tp_inv_long = max(hi, cu) + tick_buf * tick_size

            # TP distance filter (renamed from max_sl_points in original)
            tp_dist_inv_short = c - raw_tp_inv_short  # risk for inv short = entry - TP
            tp_dist_inv_long = raw_tp_inv_long - c     # risk for inv long  = TP - entry
            tp_inv_short_ok = tp_dist_inv_short <= max_tp_points
            tp_inv_long_ok = tp_dist_inv_long <= max_tp_points

            last_confirmed_hw_arr[i] = last_confirmed_hw
            last_confirmed_hw_val_arr[i] = last_confirmed_hw_val

            # ---------------------------------------------------------------
            # INVERSE SHORT entry (triggered by original LONG conditions)
            # Original long: hmaBreakLong, lastHW==1, not deltaShort, cloudLong, hwLong
            # ---------------------------------------------------------------
            if (
                hma_break_long
                and last_confirmed_hw == 1
                and not delta_short_on
                and cloud_long_ok
                and hw_long_allowed
                and hw_range_ok
                and tp_inv_short_ok
            ):
                entry = round_tick(c)
                tp = round_tick(raw_tp_inv_short)
                risk = entry - tp                   # = close - slLong (riskInvShort in Pine)
                sl = round_tick(entry + min(risk * rr_partial, tp_points))

                short_entries[i] = True
                sl_short_arr[i] = sl
                tp1_short_arr[i] = tp
                size_risk_short_arr[i] = tp        # size on TP distance, not SL distance

            # ---------------------------------------------------------------
            # INVERSE LONG entry (triggered by original SHORT conditions)
            # Original short: hmaBreakShort, lastHW==-1, not deltaLong, cloudShort, hwShort
            # ---------------------------------------------------------------
            if (
                hma_break_short
                and last_confirmed_hw == -1
                and not delta_long_on
                and cloud_short_ok
                and hw_short_allowed
                and hw_range_ok
                and tp_inv_long_ok
            ):
                entry = round_tick(c)
                tp = round_tick(raw_tp_inv_long)
                risk = tp - entry                   # = slShort - close (riskInvLong in Pine)
                sl = round_tick(entry - min(risk * rr_partial, tp_points))

                long_entries[i] = True
                sl_long_arr[i] = sl
                tp1_long_arr[i] = tp
                size_risk_long_arr[i] = tp          # size on TP distance, not SL distance

        debug_frame = pd.DataFrame(
            {
                "Open": open_,
                "High": high,
                "Low": low,
                "Close": close,
                "Volume": volume,
                "src_ema": src_ema,
                "canal_upper": canal_upper_s,
                "canal_lower": canal_lower_s,
                "canal_green": canal_green_s.astype(int),
                "osc_sig": osc_sig,
                "osc_sgd": osc_sgd,
                "mfi": mfi,
                "mfi_ref_line": cloud_ref_arr,
                "mfi_cloud_line": cloud_line_arr,
                "cloud_long_allowed": cloud_long_arr.astype(int),
                "cloud_short_allowed": cloud_short_arr.astype(int),
                "last_confirmed_hw": last_confirmed_hw_arr,
                "last_confirmed_hw_value": last_confirmed_hw_val_arr,
                "delta_long_on": delta_long_arr.astype(int),
                "delta_short_on": delta_short_arr.astype(int),
                "candle_ok": candle_ok_arr.astype(int),
                "hma_break_long": hma_break_long_arr.astype(int),
                "hma_break_short": hma_break_short_arr.astype(int),
                "inv_long_entry": long_entries.astype(int),
                "inv_short_entry": short_entries.astype(int),
                "sl_long": sl_long_arr,
                "sl_short": sl_short_arr,
                "tp1_long": tp1_long_arr,
                "tp1_short": tp1_short_arr,
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
            # TP levels passed as size_risk so the simulator sizes on TP distance
            "size_risk_long": pd.Series(size_risk_long_arr, index=data.index),
            "size_risk_short": pd.Series(size_risk_short_arr, index=data.index),
            # Canal series drive the inverse canal exit
            "canal_lower": canal_lower_s,
            "canal_upper": canal_upper_s,
            # Required by simulator API
            "ema_main": src_ema,
            "ema_secondary": src_ema,
            "cooldown_bars": p["cooldown_bars"],
            "debug_frame": debug_frame,
        }
