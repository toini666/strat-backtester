"""
HMA-SSL-Osci v2 strategy.

Translated from Pinescripts/HMA-SSL-Osci-v2.txt.

This version is intentionally separate from HMASSLOsci v1.  It reuses the
shared indicator helpers, but its entry direction, stop source, HyperWave
partial, breakeven, and HMA final-exit state follow the v2 PineScript.
"""

from typing import Any, Dict
import math

import numpy as np
import pandas as pd

from .hma_ssl_osci import HMASSLOsci


class HMASSLOsciV2(HMASSLOsci):
    """HMA ribbon + SSL Keltner channel + 4Kings oscillator + MFI cloud, v2."""

    name = "HMASSLOsciV2"

    default_params = {
        # HMA Ribbon
        "ema_len": 7,
        "hma1_len": 13,
        "hma2_len": 21,
        "amp_mult": 2.0,
        "hma_pol_bars": 3,
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
        # Oscillator filters (PineScript ①-⑨)
        "hw_dir_on": False,
        "hw_extreme_on": False,
        "hw_extreme": 20.0,
        "sig_extreme_on": False,
        "sig_extreme": 20.0,
        "hw_range_on": False,
        "hw_range": 10.0,
        "cloud_on": False,
        "delta_on": False,
        "cloud_zero_on": False,
        "delta_ext_on": False,
        "hma_side_on": True,
        # Risk management
        "tick_buffer": 0,
        "sl_mode": "mix",  # "cross_hma", "ssl_extreme", or "mix"
        "max_sl_points": 300.0,
        "cooldown_bars": 1,
        "max_candle_pct": 0.9,
        "hw_partial_pct": 25.0,
        # "both_hma", "break_hma", or "inversion_hma"
        "exit_mode": "break_hma",
        # Injected by engine
        "tick_size": 0.25,
    }

    param_ranges = {
        "ema_len": [9, 13, 21],
        "hma1_len": [9, 13, 21],
        "hma2_len": [17, 21, 34],
        "amp_mult": [1.5, 2.0, 2.5],
        "hma_pol_bars": [0, 3, 5],
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
        "hw_partial_pct": [0.0, 25.0, 50.0],
        "tick_buffer": [0, 1, 2],
    }

    def get_simulator_settings(self, params=None):
        p = self.get_params(params)
        settings = self.simulator_settings.copy()
        settings["tp1_execution_mode"] = "touch"
        settings["tp1_partial_pct"] = float(p.get("hw_partial_pct", 25.0)) / 100.0
        settings["tp2_partial_pct"] = 0.0
        settings["canal_exit_mode"] = p.get("exit_mode", "break_hma")
        return settings

    @staticmethod
    def _normalize_sl_mode(value: str) -> str:
        mapping = {
            "Cross HMA": "cross_hma",
            "Extrême SSL": "ssl_extreme",
            "Extreme SSL": "ssl_extreme",
            "Mix": "mix",
        }
        return mapping.get(value, value)

    def generate_signals(
        self, data: pd.DataFrame, params: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        p = self.get_params(params)

        ema_len = p["ema_len"]
        hma1_len = p["hma1_len"]
        hma2_len = p["hma2_len"]
        amp_mult = p["amp_mult"]
        hma_pol_bars = p.get("hma_pol_bars", 3)
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
        hma_side_on = p.get("hma_side_on", False)

        tick_buf = p["tick_buffer"]
        sl_mode = self._normalize_sl_mode(p.get("sl_mode", "cross_hma"))
        max_sl_points = p["max_sl_points"]
        max_candle_pct = p["max_candle_pct"]
        hw_partial_enabled = float(p.get("hw_partial_pct", 25.0)) > 0
        tick_size = p["tick_size"]

        close = data["Close"]
        open_ = data["Open"]
        high = data["High"]
        low = data["Low"]
        volume = data["Volume"]
        hl2 = (high + low) / 2
        n = len(data)

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
        np_hma1 = hma1_s.values
        np_hma2 = hma2_s.values
        np_canal_upper = canal_upper_s.values
        np_canal_lower = canal_lower_s.values
        np_canal_green = canal_green_s.values
        np_ssl_upper = ssl_upper_s.values
        np_ssl_lower = ssl_lower_s.values
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
        hma_bull_recent_arr = np.zeros(n, dtype=bool)
        hma_bear_recent_arr = np.zeros(n, dtype=bool)
        last_confirmed_hw_arr = np.full(n, np.nan)
        last_confirmed_hw_val_arr = np.full(n, np.nan)
        last_cross_lvl_hma_arr = np.full(n, np.nan)

        last_confirmed_hw = 0
        last_confirmed_hw_val = np.nan
        last_cross_lvl_hma = np.nan
        last_hma_flip_up_bar = None
        last_hma_flip_down_bar = None
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
            cu = np_canal_upper[i]
            cl = np_canal_lower[i]
            ssl_up = np_ssl_upper[i]
            ssl_lo = np_ssl_lower[i]

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
            if hw_cross_under:
                last_confirmed_hw = -1
                last_confirmed_hw_val = max(sig_i_raw, sgd_i_raw)

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
                last_cross_lvl_hma = (hma1 + hma2) / 2.0
                last_hma_flip_up_bar = i
            if hma_flip_down:
                last_cross_lvl_hma = (hma1 + hma2) / 2.0
                last_hma_flip_down_bar = i

            last_confirmed_hw_arr[i] = last_confirmed_hw
            last_confirmed_hw_val_arr[i] = last_confirmed_hw_val
            last_cross_lvl_hma_arr[i] = last_cross_lvl_hma

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
                or np.isnan(cu)
                or np.isnan(cl)
                or np.isnan(ssl_up)
                or np.isnan(ssl_lo)
            ):
                prev_delta_long_on = delta_long_on
                prev_delta_short_on = delta_short_on
                continue

            cg = bool(np_canal_green[i])

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

            delta_long_ok = not delta_on or not delta_short_on
            delta_short_ok = not delta_on or not delta_long_on

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
            hma_bull_recent_arr[i] = hma_bull_recent
            hma_bear_recent_arr[i] = hma_bear_recent

            hma_long_ok = (not cg) or hma_bull_recent
            hma_short_ok = cg or hma_bear_recent
            hma_side_long_ok = not hma_side_on or c > cu
            hma_side_short_ok = not hma_side_on or c < cl

            price_conf_long = c > ssl_up
            price_conf_short = c < ssl_lo

            cp = candle_pct(o, c)
            candle_ok = max_candle_pct == 0.0 or (
                not np.isnan(cp) and cp <= max_candle_pct
            )

            sl_buffer = tick_buf * tick_size
            sl_long_hma = last_cross_lvl_hma - sl_buffer
            sl_short_hma = last_cross_lvl_hma + sl_buffer
            sl_long_ssl = ssl_lo - sl_buffer
            sl_short_ssl = ssl_up + sl_buffer
            if sl_mode == "ssl_extreme":
                sl_raw_long = sl_long_ssl
                sl_raw_short = sl_short_ssl
            elif sl_mode == "mix":
                sl_raw_long = np.nanmin([sl_long_hma, sl_long_ssl])
                sl_raw_short = np.nanmax([sl_short_hma, sl_short_ssl])
            else:
                sl_raw_long = sl_long_hma
                sl_raw_short = sl_short_hma

            sl_dist_long = c - sl_raw_long
            sl_dist_short = sl_raw_short - c
            sl_long_ok = (
                not np.isnan(sl_raw_long)
                and sl_raw_long < c
                and sl_dist_long <= max_sl_points
            )
            sl_short_ok = (
                not np.isnan(sl_raw_short)
                and sl_raw_short > c
                and sl_dist_short <= max_sl_points
            )

            long_signal = (
                hma_long_ok
                and hma_side_long_ok
                and price_conf_long
                and osc_all_long_ok
                and candle_ok
                and sl_long_ok
            )
            short_signal = (
                hma_short_ok
                and hma_side_short_ok
                and price_conf_short
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
                "canal_upper": canal_upper_s,
                "canal_lower": canal_lower_s,
                "canal_green": canal_green_s.astype(int),
                "bbmc_ssl": bbmc_s,
                "ssl_upper": ssl_upper_s,
                "ssl_lower": ssl_lower_s,
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
                "hma_bull_recent": hma_bull_recent_arr.astype(int),
                "hma_bear_recent": hma_bear_recent_arr.astype(int),
                "last_cross_lvl_hma": last_cross_lvl_hma_arr,
                "long_entry_signal": long_entries.astype(int),
                "short_entry_signal": short_entries.astype(int),
                "sl_long": sl_long_arr,
                "sl_short": sl_short_arr,
                "param_ema_len": ema_len,
                "param_hma1_len": hma1_len,
                "param_hma2_len": hma2_len,
                "param_amp_mult": amp_mult,
                "param_hma_pol_bars": hma_pol_bars,
                "param_ssl_len": ssl_len,
                "param_ssl_mult": ssl_mult,
                "param_sl_mode": sl_mode,
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
            "partial_close_long": pd.Series(
                hw_cross_under_arr & hw_partial_enabled, index=data.index
            ),
            "partial_close_short": pd.Series(
                hw_cross_over_arr & hw_partial_enabled, index=data.index
            ),
            "canal_lower": canal_lower_s,
            "canal_upper": canal_upper_s,
            "canal_green": canal_green_s,
            "hma_flip_up": pd.Series(hma_flip_up_arr, index=data.index),
            "hma_flip_down": pd.Series(hma_flip_down_arr, index=data.index),
            "canal_exit_requires_arming": True,
            "ema_main": src_ema,
            "ema_secondary": src_ema,
            "cooldown_bars": p["cooldown_bars"],
            "debug_frame": debug_frame,
        }
