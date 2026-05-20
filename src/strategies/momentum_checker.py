"""
Momentum Checker strategy.

Translated from Pinescripts/Momentum-Checker.txt.

Eight independent confirmation modules each award points to the LONG and/or
SHORT side on every bar:

  1. Oscillator (4Kings HyperWave + Smart Money Flow):
     - HW Sens     — sign of the last confirmed HW crossover
     - HW Range    — |HW value at last cross| > i_hwLevel
     - HW Extreme  — |HW value at last cross| stays in non-extreme zone
     - SIG Extreme — |current osc_sig| stays in non-extreme zone
     - MFI Cloud   — cloud side matches the trade direction
     - Deltas      — osc.sig and mfi sign agree (or both off → both sides scored)
  2. Double EMA  — bullish/bearish break of emaPrin on the last 3 bars, +
                   secondary vs principal EMA alignment
  3. Supertrend  — trend direction
  4. Alligator   — chart-bar alignment, offset alignment, retest lips
  5. UT Bot      — buy / sell cross signal
  6. Rob Reversal — sweep-and-reverse candle pattern (no EMA filter)
  7. STC         — Schaff Trend Cycle in range, rising/falling
  8. HMA Ribbon  — close breaks the canal in the canal's own direction

Entry rules per side: ptsLong/Short ≥ threshold AND (ptsLong - ptsShort) ≥ minGap
AND candle filter ok AND not in blackout.

Exit rules: single fixed-distance TP at entry ± risk × RR (touch, full close),
single SL at lowest(low, slLookback) - buffer (long) / highest + buffer (short),
capped by slMaxPoints (TP recomputed if SL is capped). Auto-close handled by
the simulator.
"""

from __future__ import annotations

from typing import Any, Dict
import math

import numpy as np
import pandas as pd

import pandas_ta_classic as ta

from src.strategies.base import Strategy
from src.strategies.utbot_alligator_st import UTBotAlligatorST
from src.strategies.hma_ssl_osci import HMASSLOsci


class MomentumChecker(Strategy):
    """Multi-module points scoring system → single TP/SL trades."""

    name = "MomentumChecker"
    manual_exit = True
    use_simulator = True
    blackout_sensitive = True
    simulator_settings = {
        "tp1_execution_mode": "touch",   # immediate exit on TP touch (matches Pine)
        "tp1_full_exit": True,           # single TP, close 100% of position
    }

    default_params = {
        # --- Configuration principale ---
        "long_prep_threshold":  3,   # informational only (used for visual zone)
        "long_threshold":       5,
        "short_prep_threshold": 3,
        "short_threshold":      5,
        "min_gap":              4,

        # --- Filtre bougie ---
        "max_candle_pct": 0.4,

        # --- Risk Management ---
        "sl_lookback":   5,
        "sl_max_points": 100.0,
        "rr_tp":         2.0,
        "tick_buffer":   2,

        # --- 1) Oscillateur ---
        "osc_on":              True,
        "hyper_wave_length":   5,
        "signal_type":         "SMA",
        "signal_length":       3,
        "mf_length":           35,
        "mf_smooth":           6,
        "hw_filter_on":        True,
        "hw_level":            16.0,
        "hw_extreme_filter_on":  False,
        "sig_extreme_filter_on": False,
        "hw_extreme":          20.0,
        "pts_hw_sens":         1,
        "pts_hw_value":        1,
        "pts_hw_extreme":      1,
        "pts_sig_extreme":     1,
        "pts_cloud":           1,
        "pts_delta":           1,

        # --- 2) Double EMA ---
        "ema_on":          True,
        "ema_prin_len":    30,
        "ema_sec_len":     9,
        "pts_ema_break":   1,
        "pts_ema_align":   1,

        # --- 3) Supertrend ---
        "st_on":     True,
        "st_atr":    10,
        "st_mult":   3.0,
        "pts_st":    1,

        # --- 4) Alligator ---
        "alligator_on":     True,
        "jaw_length":       13,
        "teeth_length":     8,
        "lips_length":      5,
        "jaw_offset":       8,
        "teeth_offset":     5,
        "lips_offset":      3,
        "pts_alligator":    1,
        "pts_alli_offset":  1,
        "pts_retest_lips":  1,

        # --- 5) UT Bot ---
        "ut_on":             True,
        "ut_key":            1.0,
        "ut_atr_period":     10,
        "use_heikin_ashi":   False,
        "pts_ut_bot":        1,

        # --- 6) Rob Reversal (pattern only) ---
        "rob_on":  True,
        "pts_rob": 1,

        # --- 7) STC ---
        "stc_on":         True,
        "stc_length":     12,
        "stc_fast_len":   26,
        "stc_slow_len":   50,
        "stc_min_long":   1.0,
        "stc_max_long":   99.0,
        "stc_min_short":  1.0,
        "stc_max_short":  99.0,
        "pts_stc":        1,

        # --- 8) HMA Ribbon ---
        "hma_on":         True,
        "hma_ema_len":    7,
        "hma1_len":       42,
        "hma2_len":       84,
        "amp_mult":       2.0,
        "pts_hma_break":  1,

        # Injected by engine
        "tick_size": 0.25,
    }

    param_ranges = {
        "long_threshold":  [4, 5, 6, 7],
        "short_threshold": [4, 5, 6, 7],
        "min_gap":         [2, 3, 4, 5],
        "max_candle_pct":  [0.2, 0.3, 0.4, 0.6],
        "sl_lookback":     [3, 5, 7, 10],
        "sl_max_points":   [60.0, 100.0, 150.0],
        "rr_tp":           [1.5, 2.0, 2.5, 3.0],
        "tick_buffer":     [0, 1, 2, 3],
        "hw_level":        [10.0, 16.0, 20.0],
        "hw_extreme":      [15.0, 20.0, 25.0],
        "ema_prin_len":    [20, 30, 50],
        "ema_sec_len":     [5, 9, 13],
        "st_atr":          [7, 10, 14],
        "st_mult":         [2.0, 3.0, 4.0],
        "ut_key":          [0.5, 1.0, 1.5, 2.0],
        "ut_atr_period":   [7, 10, 14],
        "stc_length":      [10, 12, 16],
        "hma1_len":        [21, 42, 63],
        "hma2_len":        [42, 84, 105],
    }

    # ------------------------------------------------------------------
    # STC — Schaff Trend Cycle (matches Pine's iterative formula)
    # ------------------------------------------------------------------

    @staticmethod
    def _compute_stc(
        close: np.ndarray,
        length: int,
        fast_len: int,
        slow_len: int,
    ) -> np.ndarray:
        """Schaff Trend Cycle.

        Pine's `var float pff/pf/pfff/pff2 = 0.0` means the four state variables
        seed at 0.0 and the iterative `pf = pf[1] + 0.5 * (pff - pf[1])` smoothing
        runs from bar 0. Lowest/highest before the rolling window is full are
        treated as the previous bar's state value (matches `nz(pff[1])`).
        """
        n = len(close)
        close_s = pd.Series(close)
        fast_ema = close_s.ewm(span=fast_len, adjust=False).mean().to_numpy()
        slow_ema = close_s.ewm(span=slow_len, adjust=False).mean().to_numpy()
        macd = fast_ema - slow_ema

        # Pass 1: compute pf[i] (the EMA-smoothed %K of MACD).
        pf_arr = np.empty(n)
        pff = 0.0
        pf = 0.0
        for i in range(n):
            if not np.isnan(macd[i]):
                lo_i = max(0, i - length + 1)
                window = macd[lo_i:i + 1]
                if not np.any(np.isnan(window)):
                    rng = window.max() - window.min()
                    if rng > 0:
                        pff = (macd[i] - window.min()) / rng * 100.0
            pf = pf + 0.5 * (pff - pf)
            pf_arr[i] = pf

        # Pass 2: compute pff2 (the EMA-smoothed %K of pf) — this is the STC.
        stc = np.empty(n)
        pfff = 0.0
        pff2 = 0.0
        for i in range(n):
            lo_i = max(0, i - length + 1)
            window = pf_arr[lo_i:i + 1]
            if window.size > 0:
                rng = window.max() - window.min()
                if rng > 0:
                    pfff = (pf_arr[i] - window.min()) / rng * 100.0
            pff2 = pff2 + 0.5 * (pfff - pff2)
            stc[i] = pff2

        return stc

    # ------------------------------------------------------------------
    # Signal generation
    # ------------------------------------------------------------------

    def generate_signals(
        self, data: pd.DataFrame, params: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        p = self.get_params(params)

        # --- Pull params ---
        long_threshold  = int(p["long_threshold"])
        short_threshold = int(p["short_threshold"])
        min_gap         = int(p["min_gap"])
        max_candle_pct  = float(p["max_candle_pct"])
        sl_lookback     = int(p["sl_lookback"])
        sl_max_points   = float(p["sl_max_points"])
        rr_tp           = float(p["rr_tp"])
        tick_buffer     = int(p["tick_buffer"])
        tick_size       = float(p["tick_size"])

        osc_on              = bool(p["osc_on"])
        mL                  = int(p["hyper_wave_length"])
        sT                  = p["signal_type"]
        sL                  = int(p["signal_length"])
        mfL                 = int(p["mf_length"])
        mfS                 = int(p["mf_smooth"])
        hw_filter_on        = bool(p["hw_filter_on"])
        hw_level            = float(p["hw_level"])
        hw_ext_filter_on    = bool(p["hw_extreme_filter_on"])
        sig_ext_filter_on   = bool(p["sig_extreme_filter_on"])
        hw_extreme          = float(p["hw_extreme"])
        pts_hw_sens         = int(p["pts_hw_sens"])
        pts_hw_value        = int(p["pts_hw_value"])
        pts_hw_extreme      = int(p["pts_hw_extreme"])
        pts_sig_extreme     = int(p["pts_sig_extreme"])
        pts_cloud           = int(p["pts_cloud"])
        pts_delta           = int(p["pts_delta"])

        ema_on        = bool(p["ema_on"])
        ema_prin_len  = int(p["ema_prin_len"])
        ema_sec_len   = int(p["ema_sec_len"])
        pts_ema_break = int(p["pts_ema_break"])
        pts_ema_align = int(p["pts_ema_align"])

        st_on   = bool(p["st_on"])
        st_atr  = int(p["st_atr"])
        st_mult = float(p["st_mult"])
        pts_st  = int(p["pts_st"])

        alligator_on    = bool(p["alligator_on"])
        jaw_len         = int(p["jaw_length"])
        teeth_len       = int(p["teeth_length"])
        lips_len        = int(p["lips_length"])
        jaw_off         = int(p["jaw_offset"])
        teeth_off       = int(p["teeth_offset"])
        lips_off        = int(p["lips_offset"])
        pts_alligator   = int(p["pts_alligator"])
        pts_alli_offset = int(p["pts_alli_offset"])
        pts_retest_lips = int(p["pts_retest_lips"])

        ut_on         = bool(p["ut_on"])
        ut_key        = float(p["ut_key"])
        ut_atr_period = int(p["ut_atr_period"])
        use_ha        = bool(p["use_heikin_ashi"])
        pts_ut_bot    = int(p["pts_ut_bot"])

        rob_on  = bool(p["rob_on"])
        pts_rob = int(p["pts_rob"])

        stc_on        = bool(p["stc_on"])
        stc_length    = int(p["stc_length"])
        stc_fast_len  = int(p["stc_fast_len"])
        stc_slow_len  = int(p["stc_slow_len"])
        stc_min_long  = float(p["stc_min_long"])
        stc_max_long  = float(p["stc_max_long"])
        stc_min_short = float(p["stc_min_short"])
        stc_max_short = float(p["stc_max_short"])
        pts_stc       = int(p["pts_stc"])

        hma_on        = bool(p["hma_on"])
        hma_ema_len   = int(p["hma_ema_len"])
        hma1_len      = int(p["hma1_len"])
        hma2_len      = int(p["hma2_len"])
        amp_mult      = float(p["amp_mult"])
        pts_hma_break = int(p["pts_hma_break"])

        # --- Inputs ---
        close = data["Close"]
        open_ = data["Open"]
        high = data["High"]
        low = data["Low"]
        volume = data["Volume"]
        hl2 = (high + low) / 2.0
        n = len(data)

        np_close = close.values
        np_open = open_.values
        np_high = high.values
        np_low = low.values

        is_blackout = (
            data["is_blackout"].fillna(False).astype(bool).values
            if "is_blackout" in data.columns
            else np.zeros(n, dtype=bool)
        )

        def round_tick(price: float) -> float:
            if np.isnan(price):
                return np.nan
            if tick_size > 0:
                return round(price / tick_size) * tick_size
            return price

        # ----------------------------------------------------------------
        # 1) Oscillator + MFI cloud (reuse HMASSLOsci helpers)
        # ----------------------------------------------------------------
        osc_sig_s, osc_sgd_s = HMASSLOsci._compute_oscillator(
            close, high, low, hl2, mL, sT, sL
        )
        mfi_s = HMASSLOsci._compute_mfi(hl2, volume, mfL, mfS)
        np_osc = osc_sig_s.values
        np_sgd = osc_sgd_s.values
        mfi_vals = mfi_s.values
        cloud_long_arr, cloud_short_arr, _, _ = HMASSLOsci._compute_mfi_cloud(
            mfi_vals.copy(), mfL
        )

        # Last confirmed HW (running scalar through the loop later).
        # ----------------------------------------------------------------
        # 2) Double EMA
        # ----------------------------------------------------------------
        ema_prin = close.ewm(span=ema_prin_len, adjust=False).mean().values
        ema_sec = close.ewm(span=ema_sec_len, adjust=False).mean().values

        # ----------------------------------------------------------------
        # 3) Supertrend
        # ----------------------------------------------------------------
        atr_st = ta.atr(high, low, close, length=st_atr).values
        _, _, st_trend, _, _, _ = UTBotAlligatorST._compute_supertrend(
            np_close, np_high, np_low, atr_st, st_mult
        )

        # ----------------------------------------------------------------
        # 4) Alligator (SMMA on hl2) with chart vs offset views
        # ----------------------------------------------------------------
        hl2_np = hl2.values
        jaw_raw = UTBotAlligatorST._smma(hl2_np, jaw_len)
        teeth_raw = UTBotAlligatorST._smma(hl2_np, teeth_len)
        lips_raw = UTBotAlligatorST._smma(hl2_np, lips_len)

        jaw_chart = np.full(n, np.nan)
        teeth_chart = np.full(n, np.nan)
        lips_chart = np.full(n, np.nan)
        if jaw_off >= 0:
            jaw_chart[jaw_off:] = jaw_raw[: n - jaw_off] if jaw_off > 0 else jaw_raw
        if teeth_off >= 0:
            teeth_chart[teeth_off:] = (
                teeth_raw[: n - teeth_off] if teeth_off > 0 else teeth_raw
            )
        if lips_off >= 0:
            lips_chart[lips_off:] = (
                lips_raw[: n - lips_off] if lips_off > 0 else lips_raw
            )

        # ----------------------------------------------------------------
        # 5) UT Bot
        # ----------------------------------------------------------------
        if use_ha:
            ha_close = (np_open + np_high + np_low + np_close) / 4.0
            ut_src = ha_close
        else:
            ut_src = np_close.copy()
        atr_ut = ta.atr(high, low, close, length=ut_atr_period).values
        _, ut_buy, ut_sell = UTBotAlligatorST._compute_utbot(
            ut_src, atr_ut, ut_key
        )

        # ----------------------------------------------------------------
        # 7) STC
        # ----------------------------------------------------------------
        stc = self._compute_stc(np_close, stc_length, stc_fast_len, stc_slow_len)

        # ----------------------------------------------------------------
        # 8) HMA Ribbon — same construction as HMASSLOsci
        # ----------------------------------------------------------------
        _, hma1_s, hma2_s, canal_upper_s, canal_lower_s, canal_green_s = (
            HMASSLOsci._compute_hma_canal_full(
                close, hma_ema_len, hma1_len, hma2_len, amp_mult
            )
        )
        np_canal_upper = canal_upper_s.values
        np_canal_lower = canal_lower_s.values
        np_canal_green = canal_green_s.values

        # ----------------------------------------------------------------
        # Per-bar derived signals
        # ----------------------------------------------------------------
        long_entries = np.zeros(n, dtype=bool)
        short_entries = np.zeros(n, dtype=bool)
        sl_long_arr = np.full(n, np.nan)
        sl_short_arr = np.full(n, np.nan)
        tp1_long_arr = np.full(n, np.nan)
        tp1_short_arr = np.full(n, np.nan)
        pts_long_arr = np.zeros(n, dtype=int)
        pts_short_arr = np.zeros(n, dtype=int)
        last_hw_arr = np.zeros(n, dtype=int)

        last_confirmed_hw = 0
        last_confirmed_hw_val = np.nan

        # Min start bar — wait until the slowest chain has converged.
        start_bar = max(
            mL + sL + 2,
            mfL + mfS + 2,
            ema_prin_len * 4,
            st_atr * 4,
            ut_atr_period * 4,
            jaw_len + jaw_off + 5,
            teeth_len + teeth_off + 5,
            lips_len + lips_off + 5,
            stc_slow_len + stc_length + 5,
            int(hma_ema_len * 4 + hma2_len + math.sqrt(hma2_len)) + 5,
            sl_lookback + 1,
            3,  # for 3-bar EMA break window
        )

        for i in range(n):
            # --- Hyperwave crossover tracking (always, even before start_bar) ---
            sig_i = np_osc[i]
            sgd_i = np_sgd[i]
            sig_p = np_osc[i - 1] if i > 0 else np.nan
            sgd_p = np_sgd[i - 1] if i > 0 else np.nan
            cross_over = (
                not np.isnan(sig_i) and not np.isnan(sgd_i)
                and not np.isnan(sig_p) and not np.isnan(sgd_p)
                and sig_p <= sgd_p and sig_i > sgd_i
            )
            cross_under = (
                not np.isnan(sig_i) and not np.isnan(sgd_i)
                and not np.isnan(sig_p) and not np.isnan(sgd_p)
                and sig_p >= sgd_p and sig_i < sgd_i
            )
            if cross_over:
                last_confirmed_hw = 1
                last_confirmed_hw_val = min(sig_i, sgd_i)
            if cross_under:
                last_confirmed_hw = -1
                last_confirmed_hw_val = max(sig_i, sgd_i)
            last_hw_arr[i] = last_confirmed_hw

            if i < start_bar:
                continue

            c = np_close[i]
            o = np_open[i]
            h = np_high[i]
            lo_v = np_low[i]

            if np.isnan(c) or np.isnan(o):
                continue

            mfi_i = mfi_vals[i] if not np.isnan(mfi_vals[i]) else 0.0

            # ------------------------------------------------------------
            # 1) Oscillator (scoring)
            # ------------------------------------------------------------
            osc_hw_sens_long  = osc_on and last_confirmed_hw == 1
            osc_hw_sens_short = osc_on and last_confirmed_hw == -1

            hw_value_ok = osc_on and (
                not hw_filter_on
                or (
                    not np.isnan(last_confirmed_hw_val)
                    and abs(last_confirmed_hw_val) > hw_level
                )
            )

            hw_long_allowed = (
                not osc_on or not hw_ext_filter_on
                or np.isnan(last_confirmed_hw_val)
                or last_confirmed_hw_val <= hw_extreme
            )
            hw_short_allowed = (
                not osc_on or not hw_ext_filter_on
                or np.isnan(last_confirmed_hw_val)
                or last_confirmed_hw_val >= -hw_extreme
            )
            sig_extreme_long_ok = (
                not osc_on or not sig_ext_filter_on
                or np.isnan(sig_i)
                or sig_i <= hw_extreme
            )
            sig_extreme_short_ok = (
                not osc_on or not sig_ext_filter_on
                or np.isnan(sig_i)
                or sig_i >= -hw_extreme
            )

            osc_hw_extreme_long_ok = osc_on and hw_long_allowed
            osc_hw_extreme_short_ok = osc_on and hw_short_allowed
            osc_sig_extreme_long_ok = osc_on and sig_extreme_long_ok
            osc_sig_extreme_short_ok = osc_on and sig_extreme_short_ok

            sig_pos = (not np.isnan(sig_i)) and sig_i > 0
            sig_neg = (not np.isnan(sig_i)) and sig_i < 0
            delta_long_on  = sig_pos and mfi_i > 0
            delta_short_on = sig_neg and mfi_i < 0
            delta_off = (not delta_long_on) and (not delta_short_on)
            osc_delta_long  = osc_on and (delta_long_on or delta_off)
            osc_delta_short = osc_on and (delta_short_on or delta_off)

            osc_cloud_long  = osc_on and bool(cloud_long_arr[i])
            osc_cloud_short = osc_on and bool(cloud_short_arr[i])

            # ------------------------------------------------------------
            # 2) Double EMA — break + alignment
            # ------------------------------------------------------------
            def _ema_break_bull(j: int) -> bool:
                if j < 0:
                    return False
                cj = np_close[j]; oj = np_open[j]; ej = ema_prin[j]
                return (
                    not (np.isnan(cj) or np.isnan(oj) or np.isnan(ej))
                    and cj > oj and oj < ej and cj > ej
                )

            def _ema_break_bear(j: int) -> bool:
                if j < 0:
                    return False
                cj = np_close[j]; oj = np_open[j]; ej = ema_prin[j]
                return (
                    not (np.isnan(cj) or np.isnan(oj) or np.isnan(ej))
                    and cj < oj and oj > ej and cj < ej
                )

            ema_break_long = ema_on and (
                _ema_break_bull(i) or _ema_break_bull(i - 1) or _ema_break_bull(i - 2)
            )
            ema_break_short = ema_on and (
                _ema_break_bear(i) or _ema_break_bear(i - 1) or _ema_break_bear(i - 2)
            )

            ep_i = ema_prin[i]; es_i = ema_sec[i]
            ema_align_long  = ema_on and (not np.isnan(ep_i)) and (not np.isnan(es_i)) and es_i > ep_i
            ema_align_short = ema_on and (not np.isnan(ep_i)) and (not np.isnan(es_i)) and es_i < ep_i

            # ------------------------------------------------------------
            # 3) Supertrend
            # ------------------------------------------------------------
            st_bullish = st_on and st_trend[i] == 1
            st_bearish = st_on and st_trend[i] == -1

            # ------------------------------------------------------------
            # 4) Alligator
            # ------------------------------------------------------------
            j_c = jaw_chart[i]; t_c = teeth_chart[i]; l_c = lips_chart[i]
            j_r = jaw_raw[i];   t_r = teeth_raw[i];   l_r = lips_raw[i]

            alli_chart_bull = (
                alligator_on
                and not (np.isnan(j_c) or np.isnan(t_c) or np.isnan(l_c))
                and l_c > t_c > j_c
            )
            alli_chart_bear = (
                alligator_on
                and not (np.isnan(j_c) or np.isnan(t_c) or np.isnan(l_c))
                and l_c < t_c < j_c
            )
            alli_off_bull = (
                alligator_on
                and not (np.isnan(j_r) or np.isnan(t_r) or np.isnan(l_r))
                and l_r > t_r > j_r
            )
            alli_off_bear = (
                alligator_on
                and not (np.isnan(j_r) or np.isnan(t_r) or np.isnan(l_r))
                and l_r < t_r < j_r
            )

            retest_lips_long = (
                alligator_on and alli_chart_bull
                and not np.isnan(l_c) and lo_v <= l_c and c > l_c
            )
            retest_lips_short = (
                alligator_on and alli_chart_bear
                and not np.isnan(l_c) and h >= l_c and c < l_c
            )

            # ------------------------------------------------------------
            # 5) UT Bot
            # ------------------------------------------------------------
            ut_buy_i  = ut_on and bool(ut_buy[i])
            ut_sell_i = ut_on and bool(ut_sell[i])

            # ------------------------------------------------------------
            # 6) Rob Reversal (pattern only — no EMA filter, no osc filter)
            # ------------------------------------------------------------
            if i > 0:
                barA_o = np_open[i - 1]; barA_c = np_close[i - 1]
                barA_h = np_high[i - 1]; barA_l = np_low[i - 1]
                barA_bear = barA_c < barA_o
                barA_bull = barA_c > barA_o
                body_high = max(barA_o, barA_c)
                body_low = min(barA_o, barA_c)
                rob_long = (
                    rob_on and barA_bear
                    and lo_v < (barA_l - tick_size)
                    and c > body_low and c < body_high
                )
                rob_short = (
                    rob_on and barA_bull
                    and h > (barA_h + tick_size)
                    and c < body_high and c > body_low
                )
            else:
                rob_long = False
                rob_short = False

            # ------------------------------------------------------------
            # 7) STC
            # ------------------------------------------------------------
            stc_i = stc[i]
            stc_prev = stc[i - 1] if i > 0 else np.nan
            stc_rising = (not np.isnan(stc_i)) and (not np.isnan(stc_prev)) and stc_i > stc_prev
            stc_falling = (not np.isnan(stc_i)) and (not np.isnan(stc_prev)) and stc_i < stc_prev
            stc_long_ok = (
                stc_on and (not np.isnan(stc_i))
                and stc_i >= stc_min_long and stc_i <= stc_max_long
                and stc_rising
            )
            stc_short_ok = (
                stc_on and (not np.isnan(stc_i))
                and stc_i >= stc_min_short and stc_i <= stc_max_short
                and stc_falling
            )

            # ------------------------------------------------------------
            # 8) HMA Ribbon
            # ------------------------------------------------------------
            cu = np_canal_upper[i]; cl = np_canal_lower[i]; cg = bool(np_canal_green[i])
            hma_break_long = (
                hma_on and (not np.isnan(cu)) and cg and c > cu
            )
            hma_break_short = (
                hma_on and (not np.isnan(cl)) and (not cg) and c < cl
            )

            # ------------------------------------------------------------
            # Points totals
            # ------------------------------------------------------------
            pts_long = 0
            pts_long += pts_hw_sens     if osc_hw_sens_long       else 0
            pts_long += pts_hw_value    if hw_value_ok            else 0
            pts_long += pts_hw_extreme  if osc_hw_extreme_long_ok else 0
            pts_long += pts_sig_extreme if osc_sig_extreme_long_ok else 0
            pts_long += pts_cloud       if osc_cloud_long         else 0
            pts_long += pts_delta       if osc_delta_long         else 0
            pts_long += pts_ema_break   if ema_break_long         else 0
            pts_long += pts_ema_align   if ema_align_long         else 0
            pts_long += pts_st          if st_bullish             else 0
            pts_long += pts_alligator   if alli_chart_bull        else 0
            pts_long += pts_alli_offset if alli_off_bull          else 0
            pts_long += pts_retest_lips if retest_lips_long       else 0
            pts_long += pts_ut_bot      if ut_buy_i               else 0
            pts_long += pts_rob         if rob_long               else 0
            pts_long += pts_stc         if stc_long_ok            else 0
            pts_long += pts_hma_break   if hma_break_long         else 0

            pts_short = 0
            pts_short += pts_hw_sens     if osc_hw_sens_short       else 0
            pts_short += pts_hw_value    if hw_value_ok             else 0
            pts_short += pts_hw_extreme  if osc_hw_extreme_short_ok else 0
            pts_short += pts_sig_extreme if osc_sig_extreme_short_ok else 0
            pts_short += pts_cloud       if osc_cloud_short         else 0
            pts_short += pts_delta       if osc_delta_short         else 0
            pts_short += pts_ema_break   if ema_break_short         else 0
            pts_short += pts_ema_align   if ema_align_short         else 0
            pts_short += pts_st          if st_bearish              else 0
            pts_short += pts_alligator   if alli_chart_bear         else 0
            pts_short += pts_alli_offset if alli_off_bear           else 0
            pts_short += pts_retest_lips if retest_lips_short       else 0
            pts_short += pts_ut_bot      if ut_sell_i               else 0
            pts_short += pts_rob         if rob_short               else 0
            pts_short += pts_stc         if stc_short_ok            else 0
            pts_short += pts_hma_break   if hma_break_short         else 0

            pts_long_arr[i] = pts_long
            pts_short_arr[i] = pts_short

            # ------------------------------------------------------------
            # Candle size filter
            # ------------------------------------------------------------
            if c == 0:
                candle_ok = False
            else:
                candle_pct = abs(c - o) / c * 100.0
                candle_ok = candle_pct <= max_candle_pct

            # ------------------------------------------------------------
            # Entry conditions (Pine: long branch evaluated first)
            # ------------------------------------------------------------
            gap_long_ok = (pts_long - pts_short) >= min_gap
            gap_short_ok = (pts_short - pts_long) >= min_gap
            long_entry = (
                pts_long >= long_threshold
                and gap_long_ok
                and candle_ok
                and not is_blackout[i]
            )
            short_entry = (
                pts_short >= short_threshold
                and gap_short_ok
                and candle_ok
                and not is_blackout[i]
            )

            if long_entry:
                lookback_start = max(0, i - sl_lookback + 1)
                lowest_low = np.nanmin(np_low[lookback_start:i + 1])
                calc_entry = c
                raw_sl = lowest_low - tick_buffer * tick_size
                risk = calc_entry - raw_sl
                if risk > sl_max_points:
                    risk = sl_max_points
                if risk <= 0:
                    continue
                actual_sl = round_tick(calc_entry - risk)
                actual_tp = round_tick(calc_entry + risk * rr_tp)
                long_entries[i] = True
                sl_long_arr[i] = actual_sl
                tp1_long_arr[i] = actual_tp
            elif short_entry:
                lookback_start = max(0, i - sl_lookback + 1)
                highest_high = np.nanmax(np_high[lookback_start:i + 1])
                calc_entry = c
                raw_sl = highest_high + tick_buffer * tick_size
                risk = raw_sl - calc_entry
                if risk > sl_max_points:
                    risk = sl_max_points
                if risk <= 0:
                    continue
                actual_sl = round_tick(calc_entry + risk)
                actual_tp = round_tick(calc_entry - risk * rr_tp)
                short_entries[i] = True
                sl_short_arr[i] = actual_sl
                tp1_short_arr[i] = actual_tp

        # ----------------------------------------------------------------
        # Debug frame
        # ----------------------------------------------------------------
        debug_frame = pd.DataFrame(
            {
                "Open": open_,
                "High": high,
                "Low": low,
                "Close": close,
                "osc_sig": osc_sig_s,
                "osc_sgd": osc_sgd_s,
                "mfi": mfi_s,
                "last_confirmed_hw": last_hw_arr,
                "ema_prin": ema_prin,
                "ema_sec": ema_sec,
                "st_trend": st_trend,
                "jaw_chart": jaw_chart,
                "teeth_chart": teeth_chart,
                "lips_chart": lips_chart,
                "stc": stc,
                "canal_lower": canal_lower_s,
                "canal_upper": canal_upper_s,
                "canal_green": canal_green_s.astype(int),
                "pts_long": pts_long_arr,
                "pts_short": pts_short_arr,
                "is_blackout": is_blackout.astype(int),
                "long_entry_signal": long_entries.astype(int),
                "short_entry_signal": short_entries.astype(int),
                "sl_long": sl_long_arr,
                "sl_short": sl_short_arr,
                "tp1_long": tp1_long_arr,
                "tp1_short": tp1_short_arr,
            },
            index=data.index,
        )

        nan_series = pd.Series(np.full(n, np.nan), index=data.index)

        return {
            "long_entries":  pd.Series(long_entries,  index=data.index),
            "short_entries": pd.Series(short_entries, index=data.index),
            "sl_long":       pd.Series(sl_long_arr,   index=data.index),
            "sl_short":      pd.Series(sl_short_arr,  index=data.index),
            "tp1_long":      pd.Series(tp1_long_arr,  index=data.index),
            "tp1_short":     pd.Series(tp1_short_arr, index=data.index),
            # EMA-cross final exit disabled — Pine has no equivalent.
            "ema_main":      nan_series,
            "ema_secondary": nan_series,
            # cooldown_bars=1 so the simulator blocks a same-bar entry after an
            # exit, matching Pine's lastActionBar guard.
            "cooldown_bars": 1,
            "debug_frame":   debug_frame,
        }
