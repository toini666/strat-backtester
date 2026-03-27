"""
HMA-SSL-Osci strategy.

Translated from PineScript indicator HMA-SSL-Osci.txt.
Combines HMA ribbon canal + SSL Keltner channel + 4Kings Oscillator + Smart Money Flow.

Entry (Long):
  - HMA canal is green (hma1 > hma2)
  - HMA canal bottom > SSL baseline (hmaAboveSSL)
  - Close above HMA canal top AND above SSL upper band (priceConfLong)
  - All 8 oscillator filters pass
  - Candle body within max_candle_pct
  - SL distance within max_sl_points

Entry (Short):
  - HMA canal is red (hma1 <= hma2)
  - HMA canal top < SSL baseline (hmaBelowSSL)
  - Close below HMA canal bottom AND below SSL lower band (priceConfShort)
  - All 8 oscillator filters pass

SL:   lowerk_ssl - tick_buffer (Long) / upperk_ssl + tick_buffer (Short)
TP1:  min(entry + risk*rrPartial, entry+tpPoints) — bar_close_if_touched execution
TP2:  Close crosses SSL baseline partial at bar close (long: close < bbmc_ssl, short: close > bbmc_ssl)
Exit: Close below canalLower (long) or above canalUpper (short) — simulator canal logic
"""

from .base import Strategy
import pandas as pd
import numpy as np
import pandas_ta_classic as ta
from collections import deque
from typing import Dict, Any
import math
import warnings

warnings.filterwarnings("ignore", category=FutureWarning, module="pandas_ta_classic")


class HMASSLOsci(Strategy):
    """HMA ribbon + SSL Keltner channel + 4Kings Oscillator + MFI cloud."""

    name = "HMASSLOsci"
    manual_exit = True
    use_simulator = True
    simulator_settings = {
        # TP1 fires at bar close when the bar has touched the level (intrabar check,
        # but execution deferred to bar close).
        "tp1_execution_mode": "bar_close_if_touched",
    }

    default_params = {
        # HMA Ribbon
        "ema_len": 7,
        "hma1_len": 42,
        "hma2_len": 84,
        "amp_mult": 2.0,
        # SSL Channel (Gator)
        "ssl_len": 60,
        "ssl_mult": 0.2,
        # 4Kings Oscillator
        "hyper_wave_length": 5,
        "signal_type": "SMA",   # "SMA" or "EMA"
        "signal_length": 3,
        # Smart Money Flow
        "mf_length": 35,
        "mf_smooth": 6,
        # Oscillator filters (match PineScript ①–⑧)
        "hw_dir_on": True,        # ① Sens HW (last crossover direction)
        "hw_extreme_on": True,    # ② Extrêmes HW at last cross
        "hw_extreme": 20.0,       # Threshold for ② and ③
        "sig_extreme_on": True,   # ③ Current sig extreme (same threshold as ②)
        "hw_range_on": True,      # ④ Range HW (no trade in consolidation)
        "hw_range": 10.0,         # Threshold for ④
        "cloud_on": True,         # ⑤ Nuage MFI
        "delta_on": True,         # ⑥ Deltas (also part of ⑤+⑥ gate)
        "cloud_zero_on": True,    # ⑦ Nuage <0 / >0
        "delta_ext_on": True,     # ⑧ Extinction deltas
        # Risk Management
        "tick_buffer": 0,
        "rr_partial": 2.0,
        "tp_points": 50.0,
        "max_sl_points": 100.0,
        "cooldown_bars": 1,
        "max_candle_pct": 0.3,    # 0 = disabled
        "tp1_partial_pct": 0.25,
        "tp2_partial_pct": 0.25,
        # Exit mode: "both_hma" (break OR inversion), "break_hma" (close breaks canal), "inversion_hma" (canal color changes)
        "exit_mode": "both_hma",
        # Injected by engine
        "tick_size": 0.25,
    }

    param_ranges = {
        "ema_len": [5, 7, 9],
        "hma1_len": [35, 42, 50],
        "hma2_len": [70, 84, 100],
        "amp_mult": [1.5, 2.0, 2.5],
        "ssl_len": [40, 60, 80],
        "ssl_mult": [0.1, 0.2, 0.3],
        "hyper_wave_length": [3, 5, 7],
        "signal_length": [2, 3, 4],
        "mf_length": [25, 30, 35, 40],
        "mf_smooth": [4, 6, 8],
        "hw_extreme": [15.0, 20.0, 25.0],
        "hw_range": [5.0, 10.0, 15.0],
        "max_sl_points": [50.0, 75.0, 100.0, 125.0],
        "cooldown_bars": [0, 1, 2],
        "max_candle_pct": [0.0, 0.2, 0.3, 0.4],
        "rr_partial": [1.5, 2.0, 2.5, 3.0],
        "tp_points": [30.0, 50.0, 75.0],
        "tick_buffer": [0, 1, 2],
    }

    def get_simulator_settings(self, params=None):
        p = self.get_params(params)
        settings = self.simulator_settings.copy()
        settings["tp1_partial_pct"] = p.get("tp1_partial_pct", 0.25)
        settings["tp2_partial_pct"] = p.get("tp2_partial_pct", 0.25)
        settings["canal_exit_mode"] = p.get("exit_mode", "break_hma")
        return settings

    # ------------------------------------------------------------------
    # SSL Channel (Hull MA based — matches PineScript Gator SSL)
    # ------------------------------------------------------------------

    @staticmethod
    def _hma_with_rounded_sqrt(close: pd.Series, length: int) -> pd.Series:
        """Manual HMA variant used by the SSL baseline in PineScript.

        The SSL script computes:
            ta.wma(2 * ta.wma(close, len/2) - ta.wma(close, len), round(sqrt(len)))
        which differs from Pine's ta.hma() for lengths whose sqrt is non-integer.
        """
        half_length = int(length / 2)
        sqrt_length = int(round(math.sqrt(length)))
        wmaf = ta.wma(close, length=half_length)
        wmas = ta.wma(close, length=length)
        return ta.wma(2 * wmaf - wmas, length=sqrt_length)

    @staticmethod
    def _compute_ssl(close, high, low, length, mult):
        """Compute SSL Keltner channel.

        Replicates PineScript:
            BBMC_ssl    = ta.wma(
                              2*ta.wma(close, length/2) - ta.wma(close, length),
                              math.round(math.sqrt(length))
                          )
            rangema_ssl = ta.ema(ta.tr, length)
            upperk_ssl  = BBMC_ssl + rangema_ssl * mult
            lowerk_ssl  = BBMC_ssl - rangema_ssl * mult
        """
        bbmc = HMASSLOsci._hma_with_rounded_sqrt(close, length)
        tr = ta.true_range(high, low, close)
        rangema = ta.ema(tr, length=length)
        upper = bbmc + rangema * mult
        lower = bbmc - rangema * mult
        return bbmc, upper, lower

    # ------------------------------------------------------------------
    # HMA Ribbon (identical to HMAOsci)
    # ------------------------------------------------------------------

    @staticmethod
    def _compute_hma_canal(close, ema_len, hma1_len, hma2_len, amp_mult):
        """Compute HMA ribbon canal.

        Replicates PineScript:
            srcEma  = ta.ema(close, emaLen)
            rawHma1 = ta.hma(srcEma, hma1Len)
            rawHma2 = ta.hma(srcEma, hma2Len)
            hma1    = srcEma + (rawHma1 - srcEma) * ampMult
            hma2    = srcEma + (rawHma2 - srcEma) * ampMult
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
    # 4Kings Oscillator (identical to HMAOsci / EMABreakOsc)
    # ------------------------------------------------------------------

    @staticmethod
    def _compute_oscillator(close, high, low, hl2, mL, sT, sL):
        """4Kings Oscillator: sig and sgD lines.

        Replicates PineScript:
            hi = ta.highest(mL)
            lo = ta.lowest(mL)
            av = ta.sma(hl2, mL)
            osc.sig = ta.ema(ta.linreg((close - avg(hi,lo,av)) / (hi-lo) * 100, mL, 0), sL)
            osc.sgD = sT.st(osc.sig, 2)   -- SMA(2) or EMA(2)
        """
        hi = high.rolling(window=mL).max()
        lo = low.rolling(window=mL).min()
        av = ta.sma(hl2, length=mL)
        avg_hla = (hi + lo + av) / 3
        raw_osc = (close - avg_hla) / (hi - lo + 1e-10) * 100

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
    # Smart Money Flow MFI (identical to HMAOsci / EMABreakOsc)
    # ------------------------------------------------------------------

    @staticmethod
    def _compute_mfi(hl2, volume, mfL, mfS):
        """Smart Money Flow Index centred at 0.

        Replicates PineScript: ta.sma(ta.mfi(hl2, mfL) - 50, mfS)
        """
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
    # MFI cloud tracking (identical to HMAOsci / EMABreakOsc)
    # ------------------------------------------------------------------

    @staticmethod
    def _compute_mfi_cloud(mfi_values, mfL):
        """Replicate PineScript blT/brT array tracking for MFI cloud.

        Pine initialises both arrays with [na] via array.new<float>(1, na).
        Pine's array.avg() ignores NaN values.

        Returns (cloud_long_allowed, cloud_short_allowed, ref_line, cloud_line).
        """
        n = len(mfi_values)
        cloud_long = np.zeros(n, dtype=bool)
        cloud_short = np.zeros(n, dtype=bool)
        ref_line_arr = np.full(n, np.nan)
        cloud_line_arr = np.full(n, np.nan)

        blT = deque([np.nan])  # bullish tracking
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
                # Note: Pine uses blT.avg() here (not brT.avg()), replicating original code
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

        # --- Indicators ---
        src_ema, canal_upper_s, canal_lower_s, canal_green_s = self._compute_hma_canal(
            close, ema_len, hma1_len, hma2_len, amp_mult
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

        # --- Numpy arrays ---
        np_close = close.values
        np_open = open_.values
        np_high = high.values
        np_low = low.values
        np_canal_upper = canal_upper_s.values
        np_canal_lower = canal_lower_s.values
        np_canal_green = canal_green_s.values
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

        # --- Output arrays ---
        long_entries = np.zeros(n, dtype=bool)
        short_entries = np.zeros(n, dtype=bool)
        sl_long_arr = np.full(n, np.nan)
        sl_short_arr = np.full(n, np.nan)
        tp1_long_arr = np.full(n, np.nan)
        tp1_short_arr = np.full(n, np.nan)

        # Debug arrays
        last_confirmed_hw_arr = np.full(n, np.nan)
        last_confirmed_hw_val_arr = np.full(n, np.nan)

        # --- Stateful tracking ---
        last_confirmed_hw = 0           # 1=bullish crossover, -1=bearish crossunder
        last_confirmed_hw_val = np.nan
        prev_delta_long_on = False
        prev_delta_short_on = False

        # Minimum start bar: wait for all indicators to converge.
        # Dominant: EMA(ssl_len) for SSL rangema needs ~4×ssl_len bars.
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
            bbmc = np_bbmc[i]
            ssl_up = np_ssl_upper[i]
            ssl_lo = np_ssl_lower[i]

            # Skip if any indicator has not yet converged
            if (
                np.isnan(cu) or np.isnan(cl)
                or np.isnan(bbmc) or np.isnan(ssl_up) or np.isnan(ssl_lo)
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

            # --- HW crossover / crossunder (matches Pine ta.crossover / ta.crossunder) ---
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

            # --- Delta states ---
            # Pine: deltaLongOn = oscSig > 0 and mf.mfi > 0
            delta_long_on = sig_i > 0 and mfi_i > 0
            delta_short_on = sig_i < 0 and mfi_i < 0

            # ------------------------------------------------------------------
            # 8 Oscillator Filters — mirrors PineScript exactly
            # ------------------------------------------------------------------

            # ① Sens HW: last crossover direction must match trade direction
            hw_dir_long_ok = not hw_dir_on or last_confirmed_hw == 1
            hw_dir_short_ok = not hw_dir_on or last_confirmed_hw == -1

            # ② Extrêmes HW: value at last cross must be within ±extreme
            if np.isnan(last_confirmed_hw_val):
                hw_extreme_long_ok = True
                hw_extreme_short_ok = True
            else:
                hw_extreme_long_ok = not hw_extreme_on or last_confirmed_hw_val <= hw_extreme
                hw_extreme_short_ok = not hw_extreme_on or last_confirmed_hw_val >= -hw_extreme

            # ③ Extrêmes SIG courant: current sig must be within ±extreme
            # Pine: not i_sigExtremeOn or na(oscSig) or oscSig <= i_hwExtreme
            sig_extreme_long_ok = not sig_extreme_on or np.isnan(sig_i_raw) or sig_i <= hw_extreme
            sig_extreme_short_ok = not sig_extreme_on or np.isnan(sig_i_raw) or sig_i >= -hw_extreme

            # ④ Range HW: block trade if last HW value is in consolidation range
            if np.isnan(last_confirmed_hw_val):
                hw_range_ok = True
            else:
                hw_range_ok = not hw_range_on or abs(last_confirmed_hw_val) > hw_range

            # ⑤ Nuage MFI: cloud direction must match
            cloud_long_ok = cloud_long_arr[i]
            cloud_short_ok = cloud_short_arr[i]

            # ⑥ Deltas: opposing delta must be off
            # Pine: deltaLongOk = not i_deltaOn or not deltaShortOn
            delta_long_ok = not delta_on or not delta_short_on
            delta_short_ok = not delta_on or not delta_long_on

            # ⑦ Nuage <0 / >0: MFI sign must oppose trade direction
            # Pine: cloudZeroLongOk = not i_cloudZeroOn or mf.mfi < 0
            cloud_zero_long_ok = not cloud_zero_on or mfi_i < 0
            cloud_zero_short_ok = not cloud_zero_on or mfi_i > 0

            # ⑧ Extinction deltas: opposing delta must have JUST turned off this bar
            # Pine: deltaExtLongOk = not i_deltaExtOn or (deltaShortOn[1] and not deltaShortOn)
            delta_ext_long_ok = not delta_ext_on or (prev_delta_short_on and not delta_short_on)
            delta_ext_short_ok = not delta_ext_on or (prev_delta_long_on and not delta_long_on)

            # ⑤+⑥ Combined gate (OR): cloud confirms OR delta is active
            # Pine: cloudOrDeltaLongOk = not i_cloudOn or cloudLongOk or (i_deltaOn and deltaLongOn)
            cloud_or_delta_long_ok = not cloud_on or cloud_long_ok or (delta_on and delta_long_on)
            cloud_or_delta_short_ok = not cloud_on or cloud_short_ok or (delta_on and delta_short_on)

            # Final oscillator gate (all 8 conditions)
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

            # --- Candle size filter ---
            # Pine: math.abs(close - open) / close * 100 <= maxCandlePct; 0 = disabled
            candle_ok = max_candle_pct == 0.0 or candle_pct(o, c) <= max_candle_pct

            # --- HMA vs SSL alignment ---
            # Long:  canalLower > BBMC_ssl (entire canal above SSL baseline)
            # Short: canalUpper < BBMC_ssl (entire canal below SSL baseline)
            hma_above_ssl = cl > bbmc
            hma_below_ssl = cu < bbmc

            # --- Price confirmation ---
            # Long:  close > canalUpper AND close > upperk_ssl
            # Short: close < canalLower AND close < lowerk_ssl
            price_conf_long = c > cu and c > ssl_up
            price_conf_short = c < cl and c < ssl_lo

            # --- SL levels ---
            # Pine: slLong = lowerk_ssl - tickBuffer * mintick
            sl_raw_long = ssl_lo - tick_buf * tick_size
            sl_raw_short = ssl_up + tick_buf * tick_size

            # SL distance filter
            sl_dist_long = c - sl_raw_long
            sl_dist_short = sl_raw_short - c
            sl_long_ok = sl_dist_long <= max_sl_points
            sl_short_ok = sl_dist_short <= max_sl_points

            # --- Long signal ---
            long_signal = (
                cg
                and hma_above_ssl
                and price_conf_long
                and osc_all_long_ok
                and candle_ok
                and sl_long_ok
            )

            # --- Short signal ---
            short_signal = (
                not cg
                and hma_below_ssl
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
                    # TP1: nearest of RR-based or fixed-points target
                    # Pine: math.min(calcTpLong, calcPointsTpLong)
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
                    # Pine: math.max(calcTpShort, calcPointsTpShort)
                    tp_rr = round_tick(entry - risk * rr_partial)
                    tp_pts = round_tick(entry - tp_points)
                    tp1 = max(tp_rr, tp_pts)

                    short_entries[i] = True
                    sl_short_arr[i] = sl
                    tp1_short_arr[i] = tp1

            # Update previous-bar delta states for filter ⑧
            prev_delta_long_on = delta_long_on
            prev_delta_short_on = delta_short_on

        # --- Build debug frame ---
        debug_frame = pd.DataFrame(
            {
                "Open": open_,
                "High": high,
                "Low": low,
                "Close": close,
                "src_ema": src_ema,
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
                "long_entry_signal": long_entries.astype(int),
                "short_entry_signal": short_entries.astype(int),
                "sl_long": sl_long_arr,
                "sl_short": sl_short_arr,
                "tp1_long": tp1_long_arr,
                "tp1_short": tp1_short_arr,
                # Persist effective canal/SSL params in the debug export so a CSV
                # can be matched back to the exact indicator configuration.
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
            # Canal series drive final exit in the simulator.
            "canal_lower": canal_lower_s,
            "canal_upper": canal_upper_s,
            "canal_green": canal_green_s,
            # SSL baseline: TP2 partial triggers when close crosses it (long: below, short: above).
            "ssl_baseline": bbmc_s,
            # ema_main / ema_secondary required by simulator API; canal logic takes
            # priority so these are not used for exit decisions.
            "ema_main": src_ema,
            "ema_secondary": src_ema,
            "cooldown_bars": p["cooldown_bars"],
            "debug_frame": debug_frame,
        }
