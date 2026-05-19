"""
HMA-SSL-Osci v4 strategy.

Translated from ``Pinescripts/HMA-SSL-Osci-v4.txt``.

Inherits from :class:`HMASSLOsciV3` — the indicator stack and entry-window /
HW-anchored SL logic are unchanged from v3.  v4 replaces v3's exit machinery:

  1. ``i_signalCandleSlOn`` → ``i_rejectEntryAtSlExtreme``: the entry-side
     SL filter now compares the entry candle's low/high to the **raw HW
     range** (``bullHwSlBase`` / ``bearHwSlBase``) instead of the buffered
     SL price.  With ``tick_buffer == 0`` the two conditions are identical.
  2. HW partial TP, ``block_loss_exit_before_partial`` and the fixed
     ``% du prix d'entrée en profit`` final-exit mode are **removed**.
  3. Final exit (HMA-fast/SSL cross → next HW) is now RR-gated:
     ``final_exit_min_rr == 0`` reproduces v3 behaviour (first HW after the
     cross); ``> 0`` defers the exit until the HW where current RR clears
     the threshold.
  4. Optional ``move_to_be_on_fast_hma_cross``: on the fast-HMA / SSL cross,
     if the trade is in profit, move SL to entry (marks TP1 internally so
     intra-bar hits get labelled "Breakeven").
  5. Optional ``move_to_be_on_rejected_exit``: when a final exit is deferred
     for RR reasons AND the trade is in profit, move SL to entry without
     setting TP1 (intra-bar hits stay labelled "Stop Loss").
  6. ``early_exit_fired_mode``: at entry, if hma1 is already on the wrong
     side of BBMC_ssl, the fast-HMA cross has already fired and the
     standard exit signal is lost.  Four modes:
       ``"off"``           — V3-compat: ignore the case (Python-only).
       ``"hw_rr"``         — V4 PineScript default: pre-arm the pending
                             exit at entry, exit at next HW (with RR gate).
       ``"canal_inverse"`` — exit on first close beyond opposite canal side.
       ``"next_slow_cross"`` — exit at the next opposite slow-HMA/SSL cross.

To reproduce v3 trades from v4 (with v3 defaults: no HW partial,
``signal_candle_sl_on = False``, ``block_loss_exit_before_partial = False``,
``final_exit_mode = "HMA rapide/SSL → HW"``):

  * ``reject_entry_at_sl_extreme`` = ``False``
  * ``move_to_be_on_fast_hma_cross`` = ``False``
  * ``final_exit_min_rr`` = ``0.0``
  * ``move_to_be_on_rejected_exit`` = ``False``
  * ``early_exit_fired_mode`` = ``"off"``
"""

import math
from typing import Any, Dict

import numpy as np
import pandas as pd

from .hma_ssl_osci_v3 import HMASSLOsciV3, HW_SL_LOOKAROUND


EARLY_EXIT_FIRED_MODES = ("off", "hw_rr", "canal_inverse", "next_slow_cross")


class HMASSLOsciV4(HMASSLOsciV3):
    """HMA ribbon + SSL Keltner + 4Kings + MFI cloud, v4."""

    name = "HMASSLOsciV4"

    # Defaults mirror :class:`HMASSLOsciV3`'s ``default_params`` so a V4
    # backtest with default params reproduces a V3 backtest with default
    # params (the V4-new keys default to "neutral" values). To match V4
    # PineScript defaults exactly, override these params explicitly in the
    # UI / preset.
    default_params = {
        # HMA Ribbon
        "ema_len": 13,
        "hma1_len": 13,
        "hma2_len": 21,
        "amp_mult": 2.0,
        "hma_pol_bars": 3,
        "entry_window_bars": 5,
        # SSL Channel (Gator)
        "ssl_len": 60,
        "ssl_mult": 0.2,
        # 4Kings Oscillator
        "hyper_wave_length": 5,
        "signal_type": "SMA",
        "signal_length": 3,
        # Smart Money Flow
        "mf_length": 35,
        "mf_smooth": 6,
        # Oscillator filters ①-⑧ — mirror V3 strategy defaults
        "hw_dir_on": True,
        "hw_extreme_on": True,
        "hw_extreme": 20.0,
        "sig_extreme_on": True,
        "sig_extreme": 35.0,
        "hw_range_on": False,
        "hw_range": 10.0,
        "cloud_on": False,
        "delta_on": True,
        "cloud_zero_on": False,
        "delta_ext_on": False,
        # Risk management
        "tick_buffer": 0,
        "max_sl_points": 300.0,
        "cooldown_bars": 1,
        "max_candle_pct": 0.9,
        # v4: renamed (semantic change vs v3 — compares to raw HW range, not
        # buffered SL). Default False mirrors V3's signal_candle_sl_on=False.
        "reject_entry_at_sl_extreme": False,
        "one_trade_per_entry_window": True,
        # v4-new exit parameters — neutral defaults so V4 with default params
        # reproduces V3 trades.
        "move_to_be_on_fast_hma_cross": False,
        "final_exit_min_rr": 0.0,
        "move_to_be_on_rejected_exit": False,
        # "off" = V3-compat (Python-only mode). "hw_rr", "canal_inverse",
        # "next_slow_cross" map to V4 PineScript options.
        "early_exit_fired_mode": "off",
        # Injected by engine
        "tick_size": 0.25,
    }

    param_ranges = {
        "ema_len": [5, 7, 9],
        "hma1_len": [9, 13, 21],
        "hma2_len": [17, 21, 34],
        "amp_mult": [1.5, 2.0, 2.5],
        "hma_pol_bars": [0, 3, 5],
        "entry_window_bars": [3, 5, 8],
        "ssl_len": [40, 60, 80],
        "ssl_mult": [0.1, 0.2, 0.3],
        "hyper_wave_length": [3, 5, 7],
        "signal_length": [2, 3, 4],
        "mf_length": [25, 35, 45],
        "mf_smooth": [4, 6, 8],
        "hw_extreme": [15.0, 20.0, 25.0],
        "sig_extreme": [15.0, 20.0, 25.0],
        "hw_range": [5.0, 10.0, 15.0],
        "max_sl_points": [100.0, 200.0, 300.0],
        "cooldown_bars": [0, 1, 2],
        "max_candle_pct": [0.0, 0.5, 0.9],
        "tick_buffer": [0, 1, 2],
        "reject_entry_at_sl_extreme": [True, False],
        "one_trade_per_entry_window": [True, False],
        "move_to_be_on_fast_hma_cross": [True, False],
        "final_exit_min_rr": [0.0, 0.5, 1.0],
        "move_to_be_on_rejected_exit": [True, False],
        "early_exit_fired_mode": list(EARLY_EXIT_FIRED_MODES),
    }

    def get_simulator_settings(self, params=None):
        p = self.get_params(params)
        settings = dict(self.simulator_settings)
        settings["tp1_execution_mode"] = "touch"
        # v4 has no partial TP — both partial fractions disabled.
        settings["tp1_partial_pct"] = 0.0
        settings["tp2_partial_pct"] = 0.0
        settings["canal_exit_mode"] = "v4_hw_rr"
        settings["one_trade_per_setup_window"] = bool(
            p.get("one_trade_per_entry_window", True)
        )
        settings["final_exit_min_rr"] = float(p.get("final_exit_min_rr", 0.0))
        settings["move_to_be_on_fast_hma_cross"] = bool(
            p.get("move_to_be_on_fast_hma_cross", False)
        )
        settings["move_to_be_on_rejected_exit"] = bool(
            p.get("move_to_be_on_rejected_exit", False)
        )
        mode = str(p.get("early_exit_fired_mode", "hw_rr"))
        if mode not in EARLY_EXIT_FIRED_MODES:
            raise ValueError(
                f"early_exit_fired_mode must be one of {EARLY_EXIT_FIRED_MODES}; got {mode!r}"
            )
        settings["early_exit_fired_mode"] = mode
        return settings

    def generate_signals(
        self, data: pd.DataFrame, params: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        p = self.get_params(params)

        ema_len = p["ema_len"]
        hma1_len = p["hma1_len"]
        hma2_len = p["hma2_len"]
        amp_mult = p["amp_mult"]
        hma_pol_bars = p.get("hma_pol_bars", 3)
        entry_window_bars = int(p.get("entry_window_bars", 5))
        ssl_len = p["ssl_len"]
        ssl_mult = p["ssl_mult"]
        mL = p["hyper_wave_length"]
        sT = p["signal_type"]
        sL = p["signal_length"]
        mfL = p["mf_length"]
        mfS = p["mf_smooth"]

        hw_dir_on = p["hw_dir_on"]
        hw_extreme_on = p["hw_extreme_on"]
        hw_extreme = p["hw_extreme"]
        sig_extreme_on = p["sig_extreme_on"]
        sig_extreme = p.get("sig_extreme", hw_extreme)
        hw_range_on = p["hw_range_on"]
        hw_range = p["hw_range"]
        cloud_on = p["cloud_on"]
        delta_on = p["delta_on"]
        cloud_zero_on = p["cloud_zero_on"]
        delta_ext_on = p["delta_ext_on"]

        tick_buf = p["tick_buffer"]
        max_sl_points = p["max_sl_points"]
        max_candle_pct = p["max_candle_pct"]
        # v4: filter compares the entry candle's low/high to bullHwSlBase /
        # bearHwSlBase (raw HW range), not the buffered SL price.
        reject_entry_at_sl_extreme = bool(p.get("reject_entry_at_sl_extreme", True))
        tick_size = p["tick_size"]

        close = data["Close"]
        open_ = data["Open"]
        high = data["High"]
        low = data["Low"]
        volume = data["Volume"]
        hl2 = (high + low) / 2
        n = len(data)

        # ------------------------------------------------------------------
        # Indicators (identical to v2/v3)
        # ------------------------------------------------------------------
        src_ema, hma1_s, hma2_s, canal_upper_s, canal_lower_s, canal_green_s = (
            self._compute_hma_canal_full(close, ema_len, hma1_len, hma2_len, amp_mult)
        )
        bbmc_s, ssl_upper_s, ssl_lower_s = self._compute_ssl(
            close, high, low, ssl_len, ssl_mult
        )
        osc_sig, osc_sgd = self._compute_oscillator(close, high, low, hl2, mL, sT, sL)
        mfi = self._compute_mfi(hl2, volume, mfL, mfS)

        mfi_vals = mfi.values.copy()
        cloud_long_arr, cloud_short_arr, cloud_ref_arr, cloud_line_arr = (
            self._compute_mfi_cloud(mfi_vals, mfL)
        )

        np_close = close.values
        np_open = open_.values
        np_high = high.values
        np_low = low.values
        np_hma1 = hma1_s.values
        np_hma2 = hma2_s.values
        np_bbmc = bbmc_s.values
        np_canal_upper = canal_upper_s.values
        np_canal_lower = canal_lower_s.values
        np_canal_green = canal_green_s.values
        np_osc = osc_sig.values if osc_sig is not None else np.full(n, np.nan)
        np_sgd = osc_sgd.values if osc_sgd is not None else np.full(n, np.nan)
        np_mfi = mfi_vals

        def candle_pct(o, c):
            if c == 0:
                return np.nan
            return abs(c - o) / c * 100.0

        def round_tick(price):
            if np.isnan(price):
                return np.nan
            if tick_size > 0:
                return round(price / tick_size) * tick_size
            return price

        long_entries = np.zeros(n, dtype=bool)
        short_entries = np.zeros(n, dtype=bool)
        sl_long_arr = np.full(n, np.nan)
        sl_short_arr = np.full(n, np.nan)
        tp1_long_arr = np.full(n, np.nan)
        tp1_short_arr = np.full(n, np.nan)

        hw_cross_over_arr = np.zeros(n, dtype=bool)
        hw_cross_under_arr = np.zeros(n, dtype=bool)
        hma_flip_up_arr = np.zeros(n, dtype=bool)
        hma_flip_down_arr = np.zeros(n, dtype=bool)
        last_confirmed_hw_arr = np.full(n, np.nan)
        last_confirmed_hw_val_arr = np.full(n, np.nan)
        slow_cross_long_arr = np.zeros(n, dtype=bool)
        slow_cross_short_arr = np.zeros(n, dtype=bool)
        fast_exit_long_arr = np.zeros(n, dtype=bool)
        fast_exit_short_arr = np.zeros(n, dtype=bool)
        setup_bar_long_arr = np.full(n, -1, dtype=np.int64)
        setup_bar_short_arr = np.full(n, -1, dtype=np.int64)
        # v4: HMA1 vs BBMC_ssl — used by the simulator to detect early_exit_fired at entry.
        hma1_above_ssl_arr = np.zeros(n, dtype=bool)

        last_confirmed_hw = 0
        last_confirmed_hw_val = np.nan
        last_hma_flip_up_bar = None
        last_hma_flip_down_bar = None
        last_bull_hw_bar = None
        prev_bull_hw_bar = None
        last_bear_hw_bar = None
        prev_bear_hw_bar = None
        last_long_setup_bar = None
        last_short_setup_bar = None
        prev_delta_long_on = False
        prev_delta_short_on = False

        start_bar = max(
            ema_len * 4 + hma2_len + int(math.sqrt(hma2_len)),
            ssl_len * 4,
            mfL + mfS,
            mL + sL,
        ) + 10

        for i in range(n):
            c = np_close[i]
            o = np_open[i]
            hma1 = np_hma1[i]
            hma2 = np_hma2[i]
            bbmc = np_bbmc[i]
            cu = np_canal_upper[i]
            cl = np_canal_lower[i]

            sig_i_raw = np_osc[i]
            sgd_i_raw = np_sgd[i]
            sig_p_raw = np_osc[i - 1] if i > 0 else np.nan
            sgd_p_raw = np_sgd[i - 1] if i > 0 else np.nan

            hw_cross_over = (
                not np.isnan(sig_i_raw)
                and not np.isnan(sgd_i_raw)
                and not np.isnan(sig_p_raw)
                and not np.isnan(sgd_p_raw)
                and sig_p_raw <= sgd_p_raw
                and sig_i_raw > sgd_i_raw
            )
            hw_cross_under = (
                not np.isnan(sig_i_raw)
                and not np.isnan(sgd_i_raw)
                and not np.isnan(sig_p_raw)
                and not np.isnan(sgd_p_raw)
                and sig_p_raw >= sgd_p_raw
                and sig_i_raw < sgd_i_raw
            )
            hw_cross_over_arr[i] = hw_cross_over
            hw_cross_under_arr[i] = hw_cross_under

            if hw_cross_over:
                last_confirmed_hw = 1
                last_confirmed_hw_val = min(sig_i_raw, sgd_i_raw)
                prev_bull_hw_bar = last_bull_hw_bar
                last_bull_hw_bar = i
            if hw_cross_under:
                last_confirmed_hw = -1
                last_confirmed_hw_val = max(sig_i_raw, sgd_i_raw)
                prev_bear_hw_bar = last_bear_hw_bar
                last_bear_hw_bar = i

            # HMA flips (canal colour change)
            hma_flip_up = (
                i > 0
                and not np.isnan(hma1)
                and not np.isnan(hma2)
                and not np.isnan(np_hma1[i - 1])
                and not np.isnan(np_hma2[i - 1])
                and np_hma1[i - 1] <= np_hma2[i - 1]
                and hma1 > hma2
            )
            hma_flip_down = (
                i > 0
                and not np.isnan(hma1)
                and not np.isnan(hma2)
                and not np.isnan(np_hma1[i - 1])
                and not np.isnan(np_hma2[i - 1])
                and np_hma1[i - 1] >= np_hma2[i - 1]
                and hma1 < hma2
            )
            hma_flip_up_arr[i] = hma_flip_up
            hma_flip_down_arr[i] = hma_flip_down
            if hma_flip_up:
                last_hma_flip_up_bar = i
            if hma_flip_down:
                last_hma_flip_down_bar = i

            # HMA-slow / SSL-baseline crosses + fast HMA / SSL crosses
            if i > 0:
                bbmc_p = np_bbmc[i - 1]
                hma2_p = np_hma2[i - 1]
                hma1_p = np_hma1[i - 1]
                if (
                    not np.isnan(hma2)
                    and not np.isnan(bbmc)
                    and not np.isnan(hma2_p)
                    and not np.isnan(bbmc_p)
                ):
                    if hma2 < bbmc and hma2_p > bbmc_p:
                        slow_cross_long_arr[i] = True
                        last_long_setup_bar = i
                    if hma2 > bbmc and hma2_p < bbmc_p:
                        slow_cross_short_arr[i] = True
                        last_short_setup_bar = i
                if (
                    not np.isnan(hma1)
                    and not np.isnan(bbmc)
                    and not np.isnan(hma1_p)
                    and not np.isnan(bbmc_p)
                ):
                    if hma1 > bbmc and hma1_p < bbmc_p:
                        fast_exit_long_arr[i] = True
                    if hma1 < bbmc and hma1_p > bbmc_p:
                        fast_exit_short_arr[i] = True

            # v4: structural state of hma1 vs BBMC_ssl
            if not np.isnan(hma1) and not np.isnan(bbmc):
                hma1_above_ssl_arr[i] = hma1 > bbmc

            if last_long_setup_bar is not None:
                setup_bar_long_arr[i] = last_long_setup_bar
            if last_short_setup_bar is not None:
                setup_bar_short_arr[i] = last_short_setup_bar

            last_confirmed_hw_arr[i] = last_confirmed_hw
            last_confirmed_hw_val_arr[i] = last_confirmed_hw_val

            mfi_i_raw = np_mfi[i]
            sig_i = sig_i_raw
            mfi_i = mfi_i_raw
            delta_long_on = (
                not np.isnan(sig_i) and not np.isnan(mfi_i) and sig_i > 0 and mfi_i > 0
            )
            delta_short_on = (
                not np.isnan(sig_i) and not np.isnan(mfi_i) and sig_i < 0 and mfi_i < 0
            )

            if (
                i < start_bar
                or np.isnan(c)
                or np.isnan(o)
                or np.isnan(hma1)
                or np.isnan(hma2)
                or np.isnan(bbmc)
                or np.isnan(cu)
                or np.isnan(cl)
            ):
                prev_delta_long_on = delta_long_on
                prev_delta_short_on = delta_short_on
                continue

            cg = bool(np_canal_green[i])

            # ---- 8 oscillator filters ----
            hw_dir_long_ok = not hw_dir_on or last_confirmed_hw == 1
            hw_dir_short_ok = not hw_dir_on or last_confirmed_hw == -1

            hw_extreme_long_ok = (
                not hw_extreme_on
                or np.isnan(last_confirmed_hw_val)
                or last_confirmed_hw_val <= hw_extreme
            )
            hw_extreme_short_ok = (
                not hw_extreme_on
                or np.isnan(last_confirmed_hw_val)
                or last_confirmed_hw_val >= -hw_extreme
            )

            sig_extreme_long_ok = (
                not sig_extreme_on or np.isnan(sig_i_raw) or sig_i_raw <= sig_extreme
            )
            sig_extreme_short_ok = (
                not sig_extreme_on or np.isnan(sig_i_raw) or sig_i_raw >= -sig_extreme
            )

            hw_range_ok = (
                not hw_range_on
                or np.isnan(last_confirmed_hw_val)
                or abs(last_confirmed_hw_val) > hw_range
            )

            cloud_long_ok = cloud_long_arr[i]
            cloud_short_ok = cloud_short_arr[i]

            both_deltas_off = (not delta_long_on) and (not delta_short_on)
            mfi_neg = (not np.isnan(mfi_i_raw)) and mfi_i_raw < 0
            mfi_pos = (not np.isnan(mfi_i_raw)) and mfi_i_raw > 0
            delta_long_ok = (
                not delta_on or delta_long_on or (both_deltas_off and mfi_neg)
            )
            delta_short_ok = (
                not delta_on or delta_short_on or (both_deltas_off and mfi_pos)
            )

            cloud_zero_long_ok = not cloud_zero_on or (
                not np.isnan(mfi_i_raw) and mfi_i_raw < 0
            )
            cloud_zero_short_ok = not cloud_zero_on or (
                not np.isnan(mfi_i_raw) and mfi_i_raw > 0
            )

            delta_ext_long_ok = not delta_ext_on or (
                prev_delta_short_on and not delta_short_on
            )
            delta_ext_short_ok = not delta_ext_on or (
                prev_delta_long_on and not delta_long_on
            )

            cloud_or_delta_long_ok = (
                not cloud_on or cloud_long_ok or (delta_on and delta_long_on)
            )
            cloud_or_delta_short_ok = (
                not cloud_on or cloud_short_ok or (delta_on and delta_short_on)
            )

            osc_all_long_ok = (
                hw_dir_long_ok
                and hw_extreme_long_ok
                and sig_extreme_long_ok
                and hw_range_ok
                and cloud_or_delta_long_ok
                and delta_long_ok
                and cloud_zero_long_ok
                and delta_ext_long_ok
            )
            osc_all_short_ok = (
                hw_dir_short_ok
                and hw_extreme_short_ok
                and sig_extreme_short_ok
                and hw_range_ok
                and cloud_or_delta_short_ok
                and delta_short_ok
                and cloud_zero_short_ok
                and delta_ext_short_ok
            )

            # ---- HMA polarity ----
            hma_bull_recent = (
                cg
                and last_hma_flip_up_bar is not None
                and (i - last_hma_flip_up_bar) <= hma_pol_bars
            )
            hma_bear_recent = (
                (not cg)
                and last_hma_flip_down_bar is not None
                and (i - last_hma_flip_down_bar) <= hma_pol_bars
            )
            hma_long_ok = (not cg) or hma_bull_recent
            hma_short_ok = cg or hma_bear_recent

            # ---- Entry window ----
            entry_window_long_ok = (
                last_long_setup_bar is not None
                and (i - last_long_setup_bar) <= entry_window_bars
            )
            entry_window_short_ok = (
                last_short_setup_bar is not None
                and (i - last_short_setup_bar) <= entry_window_bars
            )

            # ---- Candle-size filter ----
            cp = candle_pct(o, c)
            candle_ok = max_candle_pct == 0.0 or (
                not np.isnan(cp) and cp <= max_candle_pct
            )

            # ---- v4 SL: lowest/highest from the most recent valid HW cross ----
            sl_buffer = tick_buf * tick_size

            def _resolve_hw_sl_bar(last_bar, prev_bar, idx):
                if last_bar is None:
                    return None
                age = idx - last_bar
                if age > HW_SL_LOOKAROUND:
                    return last_bar
                return prev_bar

            bull_sl_bar = _resolve_hw_sl_bar(last_bull_hw_bar, prev_bull_hw_bar, i)
            bear_sl_bar = _resolve_hw_sl_bar(last_bear_hw_bar, prev_bear_hw_bar, i)
            bull_sl_age = (i - bull_sl_bar) if bull_sl_bar is not None else None
            bear_sl_age = (i - bear_sl_bar) if bear_sl_bar is not None else None
            bull_sl_ready = bull_sl_age is not None and bull_sl_age > HW_SL_LOOKAROUND
            bear_sl_ready = bear_sl_age is not None and bear_sl_age > HW_SL_LOOKAROUND

            if bull_sl_ready:
                window_len = bull_sl_age + HW_SL_LOOKAROUND + 1
                window_start = i - window_len + 1
                if window_start < 0:
                    window_start = 0
                bull_range_low = float(np.min(np_low[window_start : i + 1]))
                # v4: bullHwSlBase = raw lowest (BEFORE applying sl_buffer)
                bull_hw_sl_base = bull_range_low
                sl_raw_long = bull_range_low - sl_buffer
            else:
                bull_hw_sl_base = np.nan
                sl_raw_long = np.nan

            if bear_sl_ready:
                window_len = bear_sl_age + HW_SL_LOOKAROUND + 1
                window_start = i - window_len + 1
                if window_start < 0:
                    window_start = 0
                bear_range_high = float(np.max(np_high[window_start : i + 1]))
                bear_hw_sl_base = bear_range_high
                sl_raw_short = bear_range_high + sl_buffer
            else:
                bear_hw_sl_base = np.nan
                sl_raw_short = np.nan

            sl_dist_long = c - sl_raw_long
            sl_dist_short = sl_raw_short - c
            logical_sl_long = not np.isnan(sl_raw_long) and sl_raw_long < c
            logical_sl_short = not np.isnan(sl_raw_short) and sl_raw_short > c
            # v4: compare entry candle's low / high to the *raw* HW range
            # (bullHwSlBase / bearHwSlBase), not the buffered SL price.
            entry_not_at_sl_extreme_long_ok = not reject_entry_at_sl_extreme or (
                logical_sl_long
                and not np.isnan(bull_hw_sl_base)
                and np_low[i] > bull_hw_sl_base
            )
            entry_not_at_sl_extreme_short_ok = not reject_entry_at_sl_extreme or (
                logical_sl_short
                and not np.isnan(bear_hw_sl_base)
                and np_high[i] < bear_hw_sl_base
            )
            sl_long_ok = (
                logical_sl_long
                and entry_not_at_sl_extreme_long_ok
                and sl_dist_long <= max_sl_points
            )
            sl_short_ok = (
                logical_sl_short
                and entry_not_at_sl_extreme_short_ok
                and sl_dist_short <= max_sl_points
            )

            # ---- Entry decision ----
            long_signal = (
                entry_window_long_ok
                and hma_long_ok
                and osc_all_long_ok
                and candle_ok
                and sl_long_ok
            )
            short_signal = (
                entry_window_short_ok
                and hma_short_ok
                and osc_all_short_ok
                and candle_ok
                and sl_short_ok
            )

            if long_signal:
                long_entries[i] = True
                sl_long_arr[i] = round_tick(sl_raw_long)
            if short_signal:
                short_entries[i] = True
                sl_short_arr[i] = round_tick(sl_raw_short)

            prev_delta_long_on = delta_long_on
            prev_delta_short_on = delta_short_on

        debug_frame = pd.DataFrame(
            {
                "Open": open_,
                "High": high,
                "Low": low,
                "Close": close,
                "src_ema": src_ema,
                "hma1": hma1_s,
                "hma2": hma2_s,
                "bbmc_ssl": bbmc_s,
                "ssl_upper": ssl_upper_s,
                "ssl_lower": ssl_lower_s,
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
                "hw_cross_over": hw_cross_over_arr.astype(int),
                "hw_cross_under": hw_cross_under_arr.astype(int),
                "last_confirmed_hw": last_confirmed_hw_arr,
                "last_confirmed_hw_value": last_confirmed_hw_val_arr,
                "hma_flip_up": hma_flip_up_arr.astype(int),
                "hma_flip_down": hma_flip_down_arr.astype(int),
                "slow_cross_long": slow_cross_long_arr.astype(int),
                "slow_cross_short": slow_cross_short_arr.astype(int),
                "fast_exit_long": fast_exit_long_arr.astype(int),
                "fast_exit_short": fast_exit_short_arr.astype(int),
                "setup_bar_long": setup_bar_long_arr,
                "setup_bar_short": setup_bar_short_arr,
                "hma1_above_ssl": hma1_above_ssl_arr.astype(int),
                "long_entry_signal": long_entries.astype(int),
                "short_entry_signal": short_entries.astype(int),
                "sl_long": sl_long_arr,
                "sl_short": sl_short_arr,
                "param_ema_len": ema_len,
                "param_hma1_len": hma1_len,
                "param_hma2_len": hma2_len,
                "param_amp_mult": amp_mult,
                "param_hma_pol_bars": hma_pol_bars,
                "param_entry_window_bars": entry_window_bars,
                "param_ssl_len": ssl_len,
                "param_ssl_mult": ssl_mult,
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
            "disable_price_tp1": True,
            # v4: no HW partial close (PineScript V4 removed this feature).
            "canal_lower": canal_lower_s,
            "canal_upper": canal_upper_s,
            "canal_green": canal_green_s,
            "hma_flip_up": pd.Series(hma_flip_up_arr, index=data.index),
            "hma_flip_down": pd.Series(hma_flip_down_arr, index=data.index),
            "fast_hma_exit_long": pd.Series(fast_exit_long_arr, index=data.index),
            "fast_hma_exit_short": pd.Series(fast_exit_short_arr, index=data.index),
            "hw_cross_over": pd.Series(hw_cross_over_arr, index=data.index),
            "hw_cross_under": pd.Series(hw_cross_under_arr, index=data.index),
            "setup_bar_long": pd.Series(setup_bar_long_arr, index=data.index),
            "setup_bar_short": pd.Series(setup_bar_short_arr, index=data.index),
            # v4-specific signals consumed by the simulator
            "hma1_above_ssl": pd.Series(hma1_above_ssl_arr, index=data.index),
            "slow_cross_long": pd.Series(slow_cross_long_arr, index=data.index),
            "slow_cross_short": pd.Series(slow_cross_short_arr, index=data.index),
            "ema_main": src_ema,
            "ema_secondary": src_ema,
            "cooldown_bars": p["cooldown_bars"],
            "debug_frame": debug_frame,
        }
