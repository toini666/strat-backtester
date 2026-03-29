"""
EMA Break + Oscillator strategy.

Translated from PineScript indicator EMA-Break-Osc.txt.
Uses 4Kings Oscillator + Smart Money Flow for confirmation.

Entry: EMA break (price crosses main EMA) confirmed by oscillator crossover,
       delta alignment, and MFI cloud conditions.
Exit: Stop loss, TP partial (RR-based or fixed points), TP2 on secondary EMA cross,
      breakeven after TP1, or EMA cross exit.
"""

from .base import Strategy
import pandas as pd
import numpy as np
import pandas_ta_classic as ta
from typing import Dict, Any, Tuple
import warnings

warnings.filterwarnings('ignore', category=FutureWarning, module='pandas_ta_classic')


class EMABreakOsc(Strategy):
    """EMA Break + Oscillator — reversal on EMA cross confirmed by 4Kings + MFI."""

    name = "EMABreakOsc"
    manual_exit = True
    # Flag: this strategy uses the new event-driven simulator
    use_simulator = True
    blackout_sensitive = True
    simulator_settings = {
        "tp1_execution_mode": "bar_close_if_touched",
    }

    default_params = {
        # EMA
        "ema_length": 30,
        "ema2_length": 10,

        # 4Kings Oscillator
        "hyper_wave_length": 5,
        "signal_type": "SMA",
        "signal_length": 3,

        # Smart Money Flow
        "mf_length": 35,
        "mf_smooth": 6,

        # Filters
        "break_wait_bars": 2,
        "hw_filter_on": True,
        "hw_level": 16.0,
        "hw_extreme_filter_on": False,
        "hw_extreme": 20.0,
        "cooldown_bars": 1,
        "max_candle_pct": 0.4,
        "require_ema_alignment": False,

        # Risk Management
        "tick_buffer": 2,
        "rr_partial": 2.0,
        "tp_points": 50.0,
        "tp1_partial_pct": 0.25,  # 25% of position closed at TP1
        "tp2_partial_pct": 0.25,  # 25% of position closed at TP2 (EMA cross)

        # Injected by engine
        "tick_size": 0.25,
    }

    param_ranges = {
        "ema_length": [20, 25, 30, 35, 40],
        "ema2_length": [8, 10, 13, 15],
        "hyper_wave_length": [3, 5, 7],
        "signal_length": [2, 3, 4],
        "mf_length": [25, 30, 35, 40],
        "mf_smooth": [4, 6, 8],
        "break_wait_bars": [0, 1, 2, 3],
        "hw_level": [10.0, 14.0, 16.0, 20.0],
        "hw_extreme": [15.0, 18.0, 20.0, 25.0],
        "cooldown_bars": [0, 1, 2],
        "max_candle_pct": [0.3, 0.4, 0.5, 0.6],
        "rr_partial": [1.5, 2.0, 2.5, 3.0],
        "tp_points": [30.0, 40.0, 50.0, 60.0],
        "tick_buffer": [1, 2, 3, 4],
    }

    def get_simulator_settings(self, params=None):
        p = self.get_params(params)
        settings = self.simulator_settings.copy()
        settings["tp1_partial_pct"] = p.get("tp1_partial_pct", 0.25)
        settings["tp2_partial_pct"] = p.get("tp2_partial_pct", 0.25)
        return settings

    # ------------------------------------------------------------------
    # Indicator computation (vectorised where possible)
    # ------------------------------------------------------------------

    @staticmethod
    def _compute_oscillator(close, high, low, hl2, mL, sT, sL):
        """4Kings Oscillator: sig and sgD lines."""
        hi = high.rolling(window=mL).max()
        lo = low.rolling(window=mL).min()
        av = ta.sma(hl2, length=mL)
        avg_hla = (hi + lo + av) / 3
        raw_osc = (close - avg_hla) / (hi - lo + 1e-10) * 100

        # Linear regression endpoint over window mL
        osc_linreg = pd.Series(np.nan, index=close.index)
        np_raw = raw_osc.values
        for i in range(mL - 1, len(close)):
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

    @staticmethod
    def _compute_mfi(hl2, volume, mfL, mfS):
        """Smart Money Flow Index centred at 0."""
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
    # MFI Cloud tracking (stateful — needs bar-by-bar loop)
    # ------------------------------------------------------------------

    @staticmethod
    def _compute_mfi_cloud(mfi_values, mfL):
        """
        Replicate the PineScript blT / brT array tracking exactly.

        Pine arrays use unshift (add to front) and pop (remove from end).
        Pine initialises both arrays with [na] via array.new<float>(1, na).
        Pine's array.avg() ignores NaN values.

        Returns four arrays:
            cloud_long_allowed  — independent line below cloud line (bullish)
            cloud_short_allowed — independent line above cloud line (bearish)
            ref_line            — tracked reference line used by the cloud logic
            cloud_line          — the current MFI value used as cloud line
        """
        n = len(mfi_values)
        cloud_long = np.zeros(n, dtype=bool)
        cloud_short = np.zeros(n, dtype=bool)
        ref_line_arr = np.full(n, np.nan)
        cloud_line_arr = np.full(n, np.nan)

        # Match Pine's initial state: array.new<float>(1, na)
        # Use deque for O(1) appendleft instead of O(n) list.insert(0, x)
        from collections import deque
        blT = deque([np.nan])  # bullish tracking
        brT = deque([np.nan])  # bearish tracking

        def _arr_avg(arr):
            """Pine's array.avg() — ignores NaN, returns NaN if all NaN."""
            valid = [v for v in arr if not np.isnan(v)]
            return np.mean(valid) if valid else np.nan

        for i in range(n):
            m = mfi_values[i]
            if np.isnan(m):
                continue

            hist_m = mfi_values[i - mfL] if i >= mfL and not np.isnan(mfi_values[i - mfL]) else np.nan

            if m > 0:
                # Shrink bearish list by ONE from the end (Pine: pop)
                if len(brT) > 1:
                    brT.pop()
                # Cap bullish list by ONE from the end (Pine: pop)
                if len(blT) > mfL:
                    blT.pop()

                bl_avg = _arr_avg(blT)
                # Pine: m > na evaluates to false
                if not np.isnan(bl_avg) and m > bl_avg:
                    blT.appendleft(m)
                else:
                    val = hist_m if (not np.isnan(hist_m) and hist_m > 0) else m
                    blT.appendleft(val)

            elif m < 0:
                # Shrink bullish list by ONE from the end (Pine: pop)
                if len(blT) > 1:
                    blT.pop()
                # Cap bearish list by ONE from the end (Pine: pop)
                if len(brT) > mfL:
                    brT.pop()

                bl_avg = _arr_avg(blT)
                # Pine: m < na evaluates to false
                if not np.isnan(bl_avg) and m < bl_avg:
                    brT.appendleft(m)
                else:
                    val = hist_m if (not np.isnan(hist_m) and hist_m < 0) else m
                    brT.appendleft(val)

            # Compute cloud lines
            if m > 0:
                ref_line = _arr_avg(blT)
            elif m < 0:
                ref_line = _arr_avg(brT)
            else:
                ref_line = np.nan

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
        """
        Compute indicators and detect entry setups.

        Returns a dict consumed by the event-driven simulator:
            long_entries, short_entries: bool arrays
            sl_long, sl_short: absolute SL price at each potential entry
            tp1_long, tp1_short: TP1 price at each potential entry
            ema_main, ema_secondary: Series for exit logic
        """
        p = self.get_params(params)

        ema_len = p["ema_length"]
        ema2_len = p["ema2_length"]
        mL = p["hyper_wave_length"]
        sT = p["signal_type"]
        sL = p["signal_length"]
        mfL = p["mf_length"]
        mfS = p["mf_smooth"]
        break_wait = p["break_wait_bars"]
        hw_filter_on = p["hw_filter_on"]
        hw_level = p["hw_level"]
        hw_extreme_filter_on = p["hw_extreme_filter_on"]
        hw_extreme = p["hw_extreme"]
        max_candle_pct = p["max_candle_pct"]
        require_align = p["require_ema_alignment"]
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

        # --- Indicators (vectorised) ---
        ema_main = ta.ema(close, length=ema_len)
        ema_sec = ta.ema(close, length=ema2_len)
        osc_sig, osc_sgd = self._compute_oscillator(close, high, low, hl2, mL, sT, sL)
        mfi = self._compute_mfi(hl2, volume, mfL, mfS)

        # MFI cloud (stateful)
        mfi_vals = mfi.values.copy()
        cloud_long_arr, cloud_short_arr, cloud_ref_arr, cloud_line_arr = self._compute_mfi_cloud(mfi_vals, mfL)

        # --- Numpy arrays for speed ---
        np_close = close.values
        np_open = open_.values
        np_high = high.values
        np_low = low.values
        np_ema = ema_main.values
        np_ema2 = ema_sec.values
        np_osc = osc_sig.values if osc_sig is not None else np.full(n, np.nan)
        np_sgd = osc_sgd.values if osc_sgd is not None else np.full(n, np.nan)
        np_mfi = mfi_vals
        is_blackout = (
            data["is_blackout"].fillna(False).astype(bool).values
            if "is_blackout" in data.columns
            else np.zeros(n, dtype=bool)
        )

        def _safe(v):
            return 0.0 if np.isnan(v) else v

        def candle_pct(o, c):
            # Match Pine: math.abs(c - o) / c * 100
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

        # --- Stateful tracking ---
        last_confirmed_hw = 0        # 1=bullish, -1=bearish
        last_confirmed_hw_val = np.nan
        bars_since_long_break = 9999
        bars_since_short_break = 9999
        last_break_long_low = np.nan
        last_break_short_high = np.nan
        last_break_long_size_ok = False
        last_break_short_size_ok = False
        start_bar = max(ema_len, mfL + mfS, mL + sL) + 5

        hw_cross_over_arr = np.zeros(n, dtype=bool)
        hw_cross_under_arr = np.zeros(n, dtype=bool)
        delta_long_arr = np.zeros(n, dtype=bool)
        delta_short_arr = np.zeros(n, dtype=bool)
        candle_pct_arr = np.full(n, np.nan)
        candle_ok_arr = np.zeros(n, dtype=bool)
        ema_break_long_arr = np.zeros(n, dtype=bool)
        ema_break_short_arr = np.zeros(n, dtype=bool)
        stored_long_arr = np.zeros(n, dtype=bool)
        stored_short_arr = np.zeros(n, dtype=bool)
        ema_align_long_arr = np.zeros(n, dtype=bool)
        ema_align_short_arr = np.zeros(n, dtype=bool)
        hw_filter_ok_arr = np.zeros(n, dtype=bool)
        hw_long_allowed_arr = np.zeros(n, dtype=bool)
        hw_short_allowed_arr = np.zeros(n, dtype=bool)
        bars_since_long_arr = np.full(n, np.nan)
        bars_since_short_arr = np.full(n, np.nan)
        last_break_long_low_arr = np.full(n, np.nan)
        last_break_short_high_arr = np.full(n, np.nan)
        last_break_long_size_ok_arr = np.zeros(n, dtype=bool)
        last_break_short_size_ok_arr = np.zeros(n, dtype=bool)
        last_confirmed_hw_arr = np.full(n, np.nan)
        last_confirmed_hw_val_arr = np.full(n, np.nan)

        for i in range(start_bar, n):
            bars_since_long_break += 1
            bars_since_short_break += 1

            c = np_close[i]
            o = np_open[i]
            h = np_high[i]
            lo_i = np_low[i]
            ema_i = np_ema[i]
            ema2_i = np_ema2[i]
            sig_i = _safe(np_osc[i])
            sgd_i = _safe(np_sgd[i])
            sig_p = _safe(np_osc[i - 1]) if i > 0 else 0.0
            sgd_p = _safe(np_sgd[i - 1]) if i > 0 else 0.0
            mfi_i = _safe(np_mfi[i])

            if np.isnan(ema_i):
                continue

            # --- HW crossover/crossunder ---
            hw_cross_over = sig_p <= sgd_p and sig_i > sgd_i
            hw_cross_under = sig_p >= sgd_p and sig_i < sgd_i
            hw_cross_over_arr[i] = hw_cross_over
            hw_cross_under_arr[i] = hw_cross_under

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

            # --- EMA break detection ---
            cpct = candle_pct(o, c)
            candle_ok = cpct <= max_candle_pct
            candle_pct_arr[i] = cpct
            candle_ok_arr[i] = candle_ok

            ema_break_long_raw = c > o and o < ema_i and c > ema_i
            ema_break_short_raw = c < o and o > ema_i and c < ema_i
            ema_break_long_arr[i] = ema_break_long_raw
            ema_break_short_arr[i] = ema_break_short_raw

            if ema_break_long_raw:
                bars_since_long_break = 0
                last_break_long_low = lo_i
                last_break_long_size_ok = candle_ok
                bars_since_short_break = 9999  # cancel pending short break

            if ema_break_short_raw:
                bars_since_short_break = 0
                last_break_short_high = h
                last_break_short_size_ok = candle_ok
                bars_since_long_break = 9999  # cancel pending long break

            # --- Entry conditions ---
            hw_filter_ok = (not hw_filter_on) or (
                not np.isnan(last_confirmed_hw_val)
                and abs(last_confirmed_hw_val) > hw_level
            )
            # Condition 2: extreme filter — long blocked if HW > +extreme, short if HW < -extreme
            if np.isnan(last_confirmed_hw_val):
                hw_long_allowed = True
                hw_short_allowed = True
            else:
                hw_long_allowed = (not hw_extreme_filter_on) or (last_confirmed_hw_val <= hw_extreme)
                hw_short_allowed = (not hw_extreme_filter_on) or (last_confirmed_hw_val >= -hw_extreme)
            stored_long_ok = (
                bars_since_long_break <= break_wait and last_break_long_size_ok
            )
            stored_short_ok = (
                bars_since_short_break <= break_wait and last_break_short_size_ok
            )
            ema_align_long = (not require_align) or (ema2_i > ema_i)
            ema_align_short = (not require_align) or (ema2_i < ema_i)
            hw_filter_ok_arr[i] = hw_filter_ok
            hw_long_allowed_arr[i] = hw_long_allowed
            hw_short_allowed_arr[i] = hw_short_allowed
            stored_long_arr[i] = stored_long_ok
            stored_short_arr[i] = stored_short_ok
            ema_align_long_arr[i] = ema_align_long
            ema_align_short_arr[i] = ema_align_short
            bars_since_long_arr[i] = bars_since_long_break
            bars_since_short_arr[i] = bars_since_short_break
            last_break_long_low_arr[i] = last_break_long_low
            last_break_short_high_arr[i] = last_break_short_high
            last_break_long_size_ok_arr[i] = last_break_long_size_ok
            last_break_short_size_ok_arr[i] = last_break_short_size_ok
            last_confirmed_hw_arr[i] = last_confirmed_hw
            last_confirmed_hw_val_arr[i] = last_confirmed_hw_val

            # Long entry
            if (
                stored_long_ok
                and last_confirmed_hw == 1
                and not delta_short_on
                and cloud_long_arr[i]
                and hw_filter_ok
                and hw_long_allowed
                and candle_ok
                and ema_align_long
                and not is_blackout[i]
            ):
                entry_price = round_tick(c)
                base_sl = last_break_long_low if bars_since_long_break > 0 else lo_i
                sl_price = round_tick(base_sl - tick_buf * tick_size)
                risk = entry_price - sl_price
                tp_rr = round_tick(entry_price + risk * rr_partial)
                tp_pts = round_tick(entry_price + tp_points)
                tp1 = min(tp_rr, tp_pts)

                long_entries[i] = True
                sl_long_arr[i] = sl_price
                tp1_long_arr[i] = tp1
                bars_since_long_break = 9999

            # Short entry
            if (
                stored_short_ok
                and last_confirmed_hw == -1
                and not delta_long_on
                and cloud_short_arr[i]
                and hw_filter_ok
                and hw_short_allowed
                and candle_ok
                and ema_align_short
                and not is_blackout[i]
            ):
                entry_price = round_tick(c)
                base_sl = last_break_short_high if bars_since_short_break > 0 else h
                sl_price = round_tick(base_sl + tick_buf * tick_size)
                risk = sl_price - entry_price
                tp_rr = round_tick(entry_price - risk * rr_partial)
                tp_pts = round_tick(entry_price - tp_points)
                tp1 = max(tp_rr, tp_pts)

                short_entries[i] = True
                sl_short_arr[i] = sl_price
                tp1_short_arr[i] = tp1
                bars_since_short_break = 9999

        debug_frame = pd.DataFrame(
            {
                "Open": open_,
                "High": high,
                "Low": low,
                "Close": close,
                "Volume": volume,
                "ema_main": ema_main,
                "ema_secondary": ema_sec,
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
                "delta_long_on": delta_long_arr.astype(int),
                "delta_short_on": delta_short_arr.astype(int),
                "candle_pct": candle_pct_arr,
                "candle_ok": candle_ok_arr.astype(int),
                "ema_break_long_raw": ema_break_long_arr.astype(int),
                "ema_break_short_raw": ema_break_short_arr.astype(int),
                "bars_since_long_break": bars_since_long_arr,
                "bars_since_short_break": bars_since_short_arr,
                "last_break_long_low": last_break_long_low_arr,
                "last_break_short_high": last_break_short_high_arr,
                "last_break_long_size_ok": last_break_long_size_ok_arr.astype(int),
                "last_break_short_size_ok": last_break_short_size_ok_arr.astype(int),
                "stored_long_ok": stored_long_arr.astype(int),
                "stored_short_ok": stored_short_arr.astype(int),
                "hw_filter_ok": hw_filter_ok_arr.astype(int),
                "hw_long_allowed": hw_long_allowed_arr.astype(int),
                "hw_short_allowed": hw_short_allowed_arr.astype(int),
                "ema_align_long": ema_align_long_arr.astype(int),
                "ema_align_short": ema_align_short_arr.astype(int),
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

        return {
            "long_entries": pd.Series(long_entries, index=data.index),
            "short_entries": pd.Series(short_entries, index=data.index),
            "sl_long": pd.Series(sl_long_arr, index=data.index),
            "sl_short": pd.Series(sl_short_arr, index=data.index),
            "tp1_long": pd.Series(tp1_long_arr, index=data.index),
            "tp1_short": pd.Series(tp1_short_arr, index=data.index),
            "ema_main": ema_main,
            "ema_secondary": ema_sec,
            "cooldown_bars": p["cooldown_bars"],
            "debug_frame": debug_frame,
        }
