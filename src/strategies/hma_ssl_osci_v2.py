"""
HMA-SSL-Osci v2 strategy.

Translated from PineScript indicator HMA-SSL-Osci-v2.txt.

Differences versus HMASSLOsci:
  - Removes the "HMA canal fully above/below SSL baseline" filter
  - Price confirmation only checks the SSL channel touch/break
  - Stop loss is anchored to the last HMA crossover midpoint
"""

from typing import Any, Dict
import math

import numpy as np
import pandas as pd

from .hma_ssl_osci import HMASSLOsci


class HMASSLOsciV2(HMASSLOsci):
    """HMA ribbon + SSL Keltner channel + 4Kings Oscillator + MFI cloud, v2."""

    name = "HMASSLOsciV2"

    def generate_signals(
        self, data: pd.DataFrame, params: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        p = self.get_params(params)

        ema_len = p["ema_len"]
        hma1_len = p["hma1_len"]
        hma2_len = p["hma2_len"]
        amp_mult = p["amp_mult"]
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
        hw_range_on = p["hw_range_on"]
        hw_range = p["hw_range"]
        cloud_on = p["cloud_on"]
        delta_on = p["delta_on"]
        cloud_zero_on = p["cloud_zero_on"]
        delta_ext_on = p["delta_ext_on"]

        tick_buf = p["tick_buffer"]
        rr_partial = p["rr_partial"]
        tp_points = p["tp_points"]
        max_sl_points = p["max_sl_points"]
        max_candle_pct = p["max_candle_pct"]
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
        np_canal_upper = canal_upper_s.values
        np_canal_lower = canal_lower_s.values
        np_canal_green = canal_green_s.values
        np_hma1 = hma1_s.values
        np_hma2 = hma2_s.values
        np_bbmc = bbmc_s.values
        np_ssl_upper = ssl_upper_s.values
        np_ssl_lower = ssl_lower_s.values
        np_osc = osc_sig.values if osc_sig is not None else np.full(n, np.nan)
        np_sgd = osc_sgd.values if osc_sgd is not None else np.full(n, np.nan)
        np_mfi = mfi_vals

        def candle_pct(o, c):
            if c == 0:
                return 999.0
            return abs(c - o) / c * 100.0

        def round_tick(price):
            if tick_size > 0:
                return round(price / tick_size) * tick_size
            return price

        long_entries = np.zeros(n, dtype=bool)
        short_entries = np.zeros(n, dtype=bool)
        sl_long_arr = np.full(n, np.nan)
        sl_short_arr = np.full(n, np.nan)
        tp1_long_arr = np.full(n, np.nan)
        tp1_short_arr = np.full(n, np.nan)

        last_confirmed_hw_arr = np.full(n, np.nan)
        last_confirmed_hw_val_arr = np.full(n, np.nan)
        last_cross_lvl_long_arr = np.full(n, np.nan)
        last_cross_lvl_short_arr = np.full(n, np.nan)

        last_confirmed_hw = 0
        last_confirmed_hw_val = np.nan
        last_cross_lvl_long = np.nan
        last_cross_lvl_short = np.nan
        prev_delta_long_on = False
        prev_delta_short_on = False

        start_bar = max(
            ema_len * 4 + hma2_len + int(math.sqrt(hma2_len)),
            ssl_len * 4,
            mfL + mfS,
            mL + sL,
        ) + 10

        for i in range(start_bar, n):
            c = np_close[i]
            o = np_open[i]
            cu = np_canal_upper[i]
            cl = np_canal_lower[i]
            cg = bool(np_canal_green[i])
            hma1 = np_hma1[i]
            hma2 = np_hma2[i]
            bbmc = np_bbmc[i]
            ssl_up = np_ssl_upper[i]
            ssl_lo = np_ssl_lower[i]

            if (
                np.isnan(cu)
                or np.isnan(cl)
                or np.isnan(hma1)
                or np.isnan(hma2)
                or np.isnan(bbmc)
                or np.isnan(ssl_up)
                or np.isnan(ssl_lo)
            ):
                prev_delta_long_on = False
                prev_delta_short_on = False
                continue

            sig_i_raw = np_osc[i]
            sig_i = 0.0 if np.isnan(sig_i_raw) else sig_i_raw
            sgd_i = 0.0 if np.isnan(np_sgd[i]) else np_sgd[i]
            sig_p = 0.0 if (i == 0 or np.isnan(np_osc[i - 1])) else np_osc[i - 1]
            sgd_p = 0.0 if (i == 0 or np.isnan(np_sgd[i - 1])) else np_sgd[i - 1]
            mfi_i_raw = np_mfi[i]
            mfi_i = 0.0 if np.isnan(mfi_i_raw) else mfi_i_raw

            hw_cross_over = sig_p <= sgd_p and sig_i > sgd_i
            hw_cross_under = sig_p >= sgd_p and sig_i < sgd_i

            if hw_cross_over:
                last_confirmed_hw = 1
                last_confirmed_hw_val = min(sig_i, sgd_i)
            if hw_cross_under:
                last_confirmed_hw = -1
                last_confirmed_hw_val = max(sig_i, sgd_i)

            last_confirmed_hw_arr[i] = last_confirmed_hw
            last_confirmed_hw_val_arr[i] = last_confirmed_hw_val

            hma_flip_up = (
                i > 0
                and not np.isnan(np_hma1[i - 1])
                and not np.isnan(np_hma2[i - 1])
                and np_hma1[i - 1] <= np_hma2[i - 1]
                and hma1 > hma2
            )
            hma_flip_down = (
                i > 0
                and not np.isnan(np_hma1[i - 1])
                and not np.isnan(np_hma2[i - 1])
                and np_hma1[i - 1] >= np_hma2[i - 1]
                and hma1 < hma2
            )
            if hma_flip_up:
                last_cross_lvl_long = (hma1 + hma2) / 2.0
            if hma_flip_down:
                last_cross_lvl_short = (hma1 + hma2) / 2.0

            last_cross_lvl_long_arr[i] = last_cross_lvl_long
            last_cross_lvl_short_arr[i] = last_cross_lvl_short

            delta_long_on = sig_i > 0 and mfi_i > 0
            delta_short_on = sig_i < 0 and mfi_i < 0

            hw_dir_long_ok = not hw_dir_on or last_confirmed_hw == 1
            hw_dir_short_ok = not hw_dir_on or last_confirmed_hw == -1

            if np.isnan(last_confirmed_hw_val):
                hw_extreme_long_ok = True
                hw_extreme_short_ok = True
            else:
                hw_extreme_long_ok = (
                    not hw_extreme_on or last_confirmed_hw_val <= hw_extreme
                )
                hw_extreme_short_ok = (
                    not hw_extreme_on or last_confirmed_hw_val >= -hw_extreme
                )

            sig_extreme_long_ok = (
                not sig_extreme_on or np.isnan(sig_i_raw) or sig_i <= hw_extreme
            )
            sig_extreme_short_ok = (
                not sig_extreme_on or np.isnan(sig_i_raw) or sig_i >= -hw_extreme
            )

            if np.isnan(last_confirmed_hw_val):
                hw_range_ok = True
            else:
                hw_range_ok = not hw_range_on or abs(last_confirmed_hw_val) > hw_range

            cloud_long_ok = cloud_long_arr[i]
            cloud_short_ok = cloud_short_arr[i]

            delta_long_ok = not delta_on or not delta_short_on
            delta_short_ok = not delta_on or not delta_long_on

            cloud_zero_long_ok = not cloud_zero_on or mfi_i < 0
            cloud_zero_short_ok = not cloud_zero_on or mfi_i > 0

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

            candle_ok = max_candle_pct == 0.0 or candle_pct(o, c) <= max_candle_pct

            price_conf_long = c > ssl_up
            price_conf_short = c < ssl_lo

            sl_raw_long = last_cross_lvl_long - tick_buf * tick_size
            sl_raw_short = last_cross_lvl_short + tick_buf * tick_size

            logical_sl_long = not np.isnan(sl_raw_long) and sl_raw_long < c
            logical_sl_short = not np.isnan(sl_raw_short) and sl_raw_short > c
            sl_dist_long = c - sl_raw_long
            sl_dist_short = sl_raw_short - c
            sl_long_ok = logical_sl_long and sl_dist_long <= max_sl_points
            sl_short_ok = logical_sl_short and sl_dist_short <= max_sl_points

            long_signal = (
                cg
                and price_conf_long
                and osc_all_long_ok
                and candle_ok
                and sl_long_ok
            )
            short_signal = (
                (not cg)
                and price_conf_short
                and osc_all_short_ok
                and candle_ok
                and sl_short_ok
            )

            if long_signal:
                entry = round_tick(c)
                sl = round_tick(sl_raw_long)
                risk = entry - sl
                if risk > 0:
                    tp_rr = round_tick(entry + risk * rr_partial)
                    tp_pts = round_tick(entry + tp_points)
                    tp1 = min(tp_rr, tp_pts)

                    long_entries[i] = True
                    sl_long_arr[i] = sl
                    tp1_long_arr[i] = tp1

            if short_signal:
                entry = round_tick(c)
                sl = round_tick(sl_raw_short)
                risk = sl - entry
                if risk > 0:
                    tp_rr = round_tick(entry - risk * rr_partial)
                    tp_pts = round_tick(entry - tp_points)
                    tp1 = max(tp_rr, tp_pts)

                    short_entries[i] = True
                    sl_short_arr[i] = sl
                    tp1_short_arr[i] = tp1

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
                "last_confirmed_hw": last_confirmed_hw_arr,
                "last_confirmed_hw_value": last_confirmed_hw_val_arr,
                "last_cross_lvl_long": last_cross_lvl_long_arr,
                "last_cross_lvl_short": last_cross_lvl_short_arr,
                "long_entry_signal": long_entries.astype(int),
                "short_entry_signal": short_entries.astype(int),
                "sl_long": sl_long_arr,
                "sl_short": sl_short_arr,
                "tp1_long": tp1_long_arr,
                "tp1_short": tp1_short_arr,
                "param_ema_len": ema_len,
                "param_hma1_len": hma1_len,
                "param_hma2_len": hma2_len,
                "param_amp_mult": amp_mult,
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
            "canal_lower": canal_lower_s,
            "canal_upper": canal_upper_s,
            "canal_green": canal_green_s,
            "ssl_baseline": bbmc_s,
            "ema_main": src_ema,
            "ema_secondary": src_ema,
            "cooldown_bars": p["cooldown_bars"],
            "debug_frame": debug_frame,
        }
