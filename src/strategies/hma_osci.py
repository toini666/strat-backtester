"""
HMA Oscillator strategy.

Translated from PineScript indicator HMA-Osci.txt.
Uses HMA Ribbon (canal) + 4Kings Oscillator + Smart Money Flow for confirmation.

Entry: HMA break (close crosses outside canal, confirmed by canal direction),
       confirmed by Hyperwave crossover direction, delta alignment, and MFI cloud.
Exit: Stop loss (canalLower/Upper ± buffer), TP1 partial (RR or fixed points,
      whichever is nearest), TP2 partial on canal re-entry, final exit on canal
      opposite-side break, or auto-close.

Key difference from EMABreakOsc:
  - Signal source is the HMA canal, not EMA breaks
  - HW extreme filter blocks entries when HW is ABOVE +extreme (long) or BELOW -extreme (short)
  - After TP1, no intra-bar SL/BE stop — position closes only on canal exit at bar close
"""

from .base import Strategy
import pandas as pd
import numpy as np
import pandas_ta_classic as ta
from collections import deque
from typing import Dict, Any
import warnings

warnings.filterwarnings("ignore", category=FutureWarning, module="pandas_ta_classic")


class HMAOsci(Strategy):
    """HMA Oscillator — canal break confirmed by 4Kings Oscillator + MFI cloud."""

    name = "HMAOsci"
    manual_exit = True
    use_simulator = True
    simulator_settings = {
        # TP1 fires at bar close if the TP level was touched during the bar
        "tp1_execution_mode": "bar_close_if_touched",
    }

    default_params = {
        # HMA Ribbon
        "ema_len": 7,
        "hma1_len": 42,
        "hma2_len": 84,
        "amp_mult": 2.0,

        # 4Kings Oscillator
        "hyper_wave_length": 5,
        "signal_type": "SMA",   # "SMA" or "EMA"
        "signal_length": 3,

        # Smart Money Flow
        "mf_length": 35,
        "mf_smooth": 6,

        # Filters
        "hw_filter_on": True,
        "hw_extreme": 20.0,     # Block long if last HW value > +extreme, short if < -extreme
        "hw_range_filter_on": False,
        "hw_range": 16.0,       # Block all trades if abs(HW) <= range (consolidation zone)
        "max_sl_points": 50.0,  # Skip trade if SL distance > this many points
        "cooldown_bars": 1,
        "max_candle_pct": 0.3,  # Skip if |close-open|/close*100 > this value

        # Risk Management
        "tick_buffer": 0,       # Extra buffer ticks beyond canal bound for SL
        "rr_partial": 2.0,      # Risk/Reward for TP1 (RR-based)
        "tp_points": 50.0,      # TP1 fixed-points fallback
        "tp1_partial_pct": 0.25,
        "tp2_partial_pct": 0.25,

        # Injected by engine
        "tick_size": 0.25,
    }

    param_ranges = {
        "ema_len": [5, 7, 9],
        "hma1_len": [35, 42, 50],
        "hma2_len": [70, 84, 100],
        "amp_mult": [1.5, 2.0, 2.5],
        "hyper_wave_length": [3, 5, 7],
        "signal_length": [2, 3, 4],
        "mf_length": [25, 30, 35, 40],
        "mf_smooth": [4, 6, 8],
        "hw_extreme": [15.0, 20.0, 25.0],
        "hw_range": [10.0, 14.0, 16.0, 20.0],
        "max_sl_points": [30.0, 40.0, 50.0, 60.0],
        "cooldown_bars": [0, 1, 2],
        "max_candle_pct": [0.2, 0.3, 0.4],
        "rr_partial": [1.5, 2.0, 2.5, 3.0],
        "tp_points": [30.0, 40.0, 50.0],
    }

    def get_simulator_settings(self, params=None):
        p = self.get_params(params)
        settings = self.simulator_settings.copy()
        settings["tp1_partial_pct"] = p.get("tp1_partial_pct", 0.25)
        settings["tp2_partial_pct"] = p.get("tp2_partial_pct", 0.25)
        return settings

    # ------------------------------------------------------------------
    # HMA calculation
    # ta.hma(src, len) = WMA(2*WMA(src, len//2) - WMA(src, len), sqrt(len))
    # Matches PineScript ta.hma() exactly via the local pandas_ta_classic library.
    # ------------------------------------------------------------------

    @staticmethod
    def _compute_hma_canal(close, ema_len, hma1_len, hma2_len, amp_mult):
        """Compute the HMA ribbon canal (upper, lower, direction).

        Replicates PineScript:
            srcEma = ta.ema(close, emaLen)
            rawHma1 = ta.hma(srcEma, hma1Len)
            rawHma2 = ta.hma(srcEma, hma2Len)
            hma1 = srcEma + (rawHma1 - srcEma) * ampMult
            hma2 = srcEma + (rawHma2 - srcEma) * ampMult
        """
        src_ema = ta.ema(close, length=ema_len)
        raw_hma1 = ta.hma(src_ema, length=hma1_len)
        raw_hma2 = ta.hma(src_ema, length=hma2_len)
        hma1 = src_ema + (raw_hma1 - src_ema) * amp_mult
        hma2 = src_ema + (raw_hma2 - src_ema) * amp_mult
        canal_upper = hma1.combine(hma2, max)
        canal_lower = hma1.combine(hma2, min)
        canal_green = hma1 > hma2
        return src_ema, canal_upper, canal_lower, canal_green

    # ------------------------------------------------------------------
    # 4Kings Oscillator (identical to EMABreakOsc)
    # ------------------------------------------------------------------

    @staticmethod
    def _compute_oscillator(close, high, low, hl2, mL, sT, sL):
        """4Kings Oscillator: sig and sgD lines."""
        hi = high.rolling(window=mL).max()
        lo = low.rolling(window=mL).min()
        av = ta.sma(hl2, length=mL)
        avg_hla = (hi + lo + av) / 3
        raw_osc = (close - avg_hla) / (hi - lo + 1e-10) * 100

        # Linear regression endpoint over window mL (matches Pine's ta.linreg)
        osc_linreg = pd.Series(np.nan, index=close.index)
        np_raw = raw_osc.values
        n = len(close)
        for i in range(mL - 1, n):
            window = np_raw[i - mL + 1 : i + 1]
            if not np.any(np.isnan(window)):
                x = np.arange(mL)
                try:
                    coeffs = np.polyfit(x, window, 1)
                    osc_linreg.iloc[i] = coeffs[0] * (mL - 1) + coeffs[1]
                except Exception:
                    osc_linreg.iloc[i] = window[-1]

        osc_sig = ta.ema(osc_linreg, length=sL)
        osc_sgd = (
            ta.sma(osc_sig, length=2) if sT == "SMA" else ta.ema(osc_sig, length=2)
        )
        return osc_sig, osc_sgd

    # ------------------------------------------------------------------
    # Smart Money Flow MFI (identical to EMABreakOsc)
    # ------------------------------------------------------------------

    @staticmethod
    def _compute_mfi(hl2, volume, mfL, mfS):
        """Smart Money Flow Index centred at 0. Matches Pine's ta.mfi(hl2, mfL) - 50."""
        typical_price = hl2
        raw_money_flow = typical_price * volume
        tp_change = typical_price.diff()

        positive_flow = raw_money_flow.where(tp_change > 0, 0.0)
        negative_flow = raw_money_flow.where(tp_change < 0, 0.0)

        positive_sum = positive_flow.rolling(window=mfL).sum()
        negative_sum = negative_flow.rolling(window=mfL).sum()

        ratio = positive_sum / (negative_sum + 1e-10)
        mfi_raw = 100 - (100 / (1 + ratio))
        return ta.sma(mfi_raw - 50, length=mfS)

    # ------------------------------------------------------------------
    # MFI cloud tracking (identical to EMABreakOsc)
    # ------------------------------------------------------------------

    @staticmethod
    def _compute_mfi_cloud(mfi_values, mfL):
        """Replicate PineScript blT/brT array tracking for MFI cloud.

        Returns (cloud_long_allowed, cloud_short_allowed, ref_line, cloud_line).
        """
        n = len(mfi_values)
        cloud_long = np.zeros(n, dtype=bool)
        cloud_short = np.zeros(n, dtype=bool)
        ref_line_arr = np.full(n, np.nan)
        cloud_line_arr = np.full(n, np.nan)

        blT = deque([np.nan])  # bullish tracking (Pine: array.new<float>(1, na))
        brT = deque([np.nan])  # bearish tracking

        def _arr_avg(arr):
            valid = [v for v in arr if not np.isnan(v)]
            return np.mean(valid) if valid else np.nan

        for i in range(n):
            m = mfi_values[i]
            if np.isnan(m):
                continue

            hist_m = (
                mfi_values[i - mfL]
                if i >= mfL and not np.isnan(mfi_values[i - mfL])
                else np.nan
            )

            if m > 0:
                if len(brT) > 1:
                    brT.pop()
                if len(blT) > mfL:
                    blT.pop()
                bl_avg = _arr_avg(blT)
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
                bl_avg = _arr_avg(blT)
                if not np.isnan(bl_avg) and m < bl_avg:
                    brT.appendleft(m)
                else:
                    val = hist_m if (not np.isnan(hist_m) and hist_m < 0) else m
                    brT.appendleft(val)

            ref_line = _arr_avg(blT) if m > 0 else (_arr_avg(brT) if m < 0 else np.nan)
            cloud_line = m
            ref_line_arr[i] = ref_line
            cloud_line_arr[i] = cloud_line

            if not np.isnan(ref_line) and cloud_line != 0:
                cloud_long[i] = ref_line < cloud_line
                cloud_short[i] = ref_line > cloud_line

        return cloud_long, cloud_short, ref_line_arr, cloud_line_arr

    # ------------------------------------------------------------------
    # Main signal generation
    # ------------------------------------------------------------------

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
        max_sl_points = p["max_sl_points"]
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

        # --- Indicators ---
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
            """Match Pine: math.abs(c - o) / c * 100"""
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

        # --- Debug arrays ---
        last_confirmed_hw_arr = np.full(n, np.nan)
        last_confirmed_hw_val_arr = np.full(n, np.nan)
        delta_long_arr = np.zeros(n, dtype=bool)
        delta_short_arr = np.zeros(n, dtype=bool)
        hma_break_long_arr = np.zeros(n, dtype=bool)
        hma_break_short_arr = np.zeros(n, dtype=bool)
        candle_ok_arr = np.zeros(n, dtype=bool)
        hw_long_allowed_arr = np.zeros(n, dtype=bool)
        hw_short_allowed_arr = np.zeros(n, dtype=bool)
        hw_range_ok_arr = np.zeros(n, dtype=bool)
        sl_long_ok_arr = np.zeros(n, dtype=bool)
        sl_short_ok_arr = np.zeros(n, dtype=bool)

        # --- Stateful tracking ---
        last_confirmed_hw = 0         # 1=bullish crossover, -1=bearish crossunder
        last_confirmed_hw_val = np.nan

        # Minimum start bar: enough warmup for all indicators to converge.
        # HMA(hma2_len) on EMA(ema_len): needs roughly ema_len*4 + hma2_len + sqrt(hma2_len)
        import math
        start_bar = max(
            ema_len * 4 + hma2_len + int(math.sqrt(hma2_len)),
            mfL + mfS,
            mL + sL,
        ) + 10

        for i in range(start_bar, n):
            c = np_close[i]
            o = np_open[i]
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

            # --- HW crossover/crossunder (Pine: ta.crossover / ta.crossunder) ---
            # crossover(a, b) = prev_a <= prev_b AND cur_a > cur_b
            hw_cross_over = sig_p <= sgd_p and sig_i > sgd_i
            hw_cross_under = sig_p >= sgd_p and sig_i < sgd_i

            if hw_cross_over:
                last_confirmed_hw = 1
                last_confirmed_hw_val = min(sig_i, sgd_i)
            if hw_cross_under:
                last_confirmed_hw = -1
                last_confirmed_hw_val = max(sig_i, sgd_i)

            # --- Delta states ---
            # Pine: deltaLongOn = osc.sig > 0 and mf.mfi > 0
            delta_long_on = sig_i > 0 and mfi_i > 0
            delta_short_on = sig_i < 0 and mfi_i < 0
            delta_long_arr[i] = delta_long_on
            delta_short_arr[i] = delta_short_on

            # --- Candle size filter ---
            cpct = candle_pct(o, c)
            candle_ok = cpct <= max_candle_pct
            candle_ok_arr[i] = candle_ok

            # --- HMA break signal ---
            # Long: canal green AND close > upper AND candle ok
            # Short: canal red AND close < lower AND candle ok
            hma_break_long = bool(cg) and c > cu and candle_ok
            hma_break_short = not bool(cg) and c < cl and candle_ok
            hma_break_long_arr[i] = hma_break_long
            hma_break_short_arr[i] = hma_break_short

            # --- HW extreme filter ---
            # Long blocked if lastConfirmedHWValue > +hwExtreme (overbought extreme)
            # Short blocked if lastConfirmedHWValue < -hwExtreme (oversold extreme)
            if np.isnan(last_confirmed_hw_val):
                hw_long_allowed = True
                hw_short_allowed = True
                hw_range_ok = True
            else:
                hw_long_allowed = (not hw_filter_on) or (last_confirmed_hw_val <= hw_extreme)
                hw_short_allowed = (not hw_filter_on) or (last_confirmed_hw_val >= -hw_extreme)
                # Condition 1: range filter — no trade if abs(HW) <= range (consolidation)
                hw_range_ok = (not hw_range_filter_on) or (abs(last_confirmed_hw_val) > hw_range)
            hw_long_allowed_arr[i] = hw_long_allowed
            hw_short_allowed_arr[i] = hw_short_allowed
            hw_range_ok_arr[i] = hw_range_ok

            # --- Cloud filter ---
            cloud_long_ok = cloud_long_arr[i]
            cloud_short_ok = cloud_short_arr[i]

            # --- SL distance filter ---
            # SL = lowest of (signal bar low, canal lower) for long;
            # highest of (signal bar high, canal upper) for short.
            raw_sl_long = min(np_low[i], cl) - tick_buf * tick_size
            raw_sl_short = max(np_high[i], cu) + tick_buf * tick_size
            sl_dist_long = c - raw_sl_long
            sl_dist_short = raw_sl_short - c
            sl_long_ok = sl_dist_long <= max_sl_points
            sl_short_ok = sl_dist_short <= max_sl_points
            sl_long_ok_arr[i] = sl_long_ok
            sl_short_ok_arr[i] = sl_short_ok

            last_confirmed_hw_arr[i] = last_confirmed_hw
            last_confirmed_hw_val_arr[i] = last_confirmed_hw_val

            # --- Long entry ---
            if (
                hma_break_long
                and last_confirmed_hw == 1
                and not delta_short_on
                and cloud_long_ok
                and hw_long_allowed
                and hw_range_ok
                and sl_long_ok
            ):
                entry = round_tick(c)
                sl = round_tick(raw_sl_long)
                risk = entry - sl
                tp_rr = round_tick(entry + risk * rr_partial)
                tp_pts = round_tick(entry + tp_points)
                tp1 = min(tp_rr, tp_pts)

                long_entries[i] = True
                sl_long_arr[i] = sl
                tp1_long_arr[i] = tp1

            # --- Short entry ---
            if (
                hma_break_short
                and last_confirmed_hw == -1
                and not delta_long_on
                and cloud_short_ok
                and hw_short_allowed
                and hw_range_ok
                and sl_short_ok
            ):
                entry = round_tick(c)
                sl = round_tick(raw_sl_short)
                risk = sl - entry
                tp_rr = round_tick(entry - risk * rr_partial)
                tp_pts = round_tick(entry - tp_points)
                tp1 = max(tp_rr, tp_pts)

                short_entries[i] = True
                sl_short_arr[i] = sl
                tp1_short_arr[i] = tp1

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
                "hw_long_allowed": hw_long_allowed_arr.astype(int),
                "hw_short_allowed": hw_short_allowed_arr.astype(int),
                "hw_range_ok": hw_range_ok_arr.astype(int),
                "sl_long_ok": sl_long_ok_arr.astype(int),
                "sl_short_ok": sl_short_ok_arr.astype(int),
                "long_entry_signal": long_entries.astype(int),
                "short_entry_signal": short_entries.astype(int),
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
            # Canal series drive close-based TP2 and final exit in simulator
            "canal_lower": canal_lower_s,
            "canal_upper": canal_upper_s,
            # ema_main / ema_secondary required by simulator API; not used for
            # exit logic when canal_lower/canal_upper are present.
            "ema_main": src_ema,
            "ema_secondary": src_ema,
            "cooldown_bars": p["cooldown_bars"],
            "debug_frame": debug_frame,
        }
