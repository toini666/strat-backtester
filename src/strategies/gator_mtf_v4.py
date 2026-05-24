"""Gator-MTF v4 strategy — multi-timeframe HMA/SSL mean-reversion.

Translated from ``Pinescripts/Gator-MTF-v4.txt``.

The backtest chart is M1 (mandatory). HMA / SSL cross detection runs on a
configurable higher *trigger* timeframe (default M7). At each M1 bar we
read the values of the **last confirmed trigger bar** — mirroring Pine's
``request.security(..., barmerge.lookahead_on)`` with ``[1]`` on every
output, which is the canonical anti-repaint idiom (always the previous
fully-closed HTF bar, identical in historical and real-time playback).

Mean-reversion convention:
    canal_vert  (HMA1 < HMA2, descending channel)  → search for LONG
    canal_rouge (HMA1 > HMA2, ascending  channel)  → search for SHORT
Entry windows open on:
    long  : ta.cross(HMA, SSL upper)  during canal_vert  on the trigger TF
    short : ta.cross(HMA, SSL lower)  during canal_rouge on the trigger TF

Four entry cases A/B/C/D (and an informative E) gate the trade by:
    C1 = trigger HMA canal colour
    C2 = M1 HMA canal colour
    C3 = M1 Smart-Money-Flow MFI sign (NOT the 4Kings oscillator)
The 4Kings oscillator's sig line is used ONLY for the "sig extreme"
weighting on cases C and D.

Exits:
    SL (lookback + min %) — initial stop or breakeven post-partial
    TP partial at RR i_partialRr (SL → BE)
    TP final  at RR i_finalRr   (close entire position)
    Auto-close at 22:00 (Brussels reference); blackouts.

⚠ PARTIAL TP IS NOT YET WIRED THROUGH THE SIMULATOR.
   Pine defaults set ``i_partialRr = 0.0`` and ``i_hwPartialPct = 0.0`` —
   the default backtest has SL + TP final only and matches Pine exactly.
   Setting BOTH parameters > 0 raises ``ValueError`` at signal generation
   time so trades never silently diverge from TradingView. To use partials,
   the simulator needs an "intra-bar full exit at fixed TP final" mode
   that takes priority over the partial; this is a separate engine task.
"""
from __future__ import annotations

import logging
import math
from typing import Any, Dict

import numpy as np
import pandas as pd
import pandas_ta_classic as ta

from src.data.recompose import recompose_bars
from src.engine.fast_indicators import (
    fast_hma,
    fast_hma_rounded_sqrt,
    rolling_linreg_last,
)

from .base import Strategy

logger = logging.getLogger(__name__)


# Trigger TF integer (minutes) → recompose_bars string.
_TF_MINUTES_TO_STR: Dict[int, str] = {
    2: "2m", 3: "3m", 5: "5m", 7: "7m",
    10: "10m", 15: "15m", 30: "30m",
    60: "1h", 240: "4h", 1440: "1d",
}


class GatorMTFv4(Strategy):
    """Gator-MTF v4 — chart M1, trigger M7 (default), mean-reversion HMA/SSL."""

    name = "GatorMTFv4"
    use_simulator = True

    simulator_settings = {
        # SL > TP final priority is achieved by mapping tp1 = tpFinalPrice
        # and enabling tp1_full_exit. The simulator closes the entire
        # position at tp1 on intra-bar touch.
        "tp1_execution_mode": "touch",
        "tp1_full_exit": True,
        "tp1_partial_pct": 0.0,
        "tp2_partial_pct": 0.0,
        # ema_main / ema_secondary are passed as NaN series so the EMA-cross
        # exit never fires; this guard prevents it even if a NaN ever leaks.
        "ema_exit_after_tp1_only": True,
    }

    default_params = {
        # Trigger TF in minutes (must be in _TF_MINUTES_TO_STR).
        "trigger_tf_minutes": 7,
        # HMA Ribbon (shared M1 + trigger).
        "ema_len": 7,
        "hma1_len": 13,
        "hma2_len": 21,
        "amp_mult": 2.0,
        "entry_window_bars_trigger": 5,
        # SSL Keltner channel (shared M1 + trigger).
        "ssl_len": 60,
        "ssl_mult": 0.2,
        # 4Kings Oscillator (M1, sig extreme filter only).
        "hyper_wave_length": 5,
        "signal_length": 3,
        # Smart-Money-Flow MFI (M1).
        "mf_length": 35,
        "mf_smooth": 6,
        # Sig extreme threshold (absolute value, single threshold).
        "sig_extreme_threshold": 20.0,
        # Cases toggle.
        "case_a_on": True,
        "case_b_on": True,
        "case_c_on": True,
        "case_d_on": True,
        # Risk management.
        "sl_lookback": 1,
        "sl_min_pct": 0.15,
        "tick_buffer": 2,
        "cooldown_bars": 7,
        "hw_partial_pct": 0.0,
        "partial_rr": 0.0,
        "final_rr": 1.0,
        "one_trade_per_window": True,
        # Injected by the engine.
        "tick_size": 0.25,
    }

    param_ranges = {
        "ema_len": [5, 7, 9],
        "hma1_len": [9, 13, 17],
        "hma2_len": [17, 21, 28],
        "amp_mult": [1.5, 2.0, 2.5],
        "entry_window_bars_trigger": [3, 5, 8],
        "ssl_len": [40, 60, 80],
        "ssl_mult": [0.15, 0.20, 0.25],
        "hyper_wave_length": [3, 5, 7],
        "signal_length": [2, 3, 4],
        "mf_length": [25, 35, 45],
        "mf_smooth": [4, 6, 8],
        "sig_extreme_threshold": [15.0, 20.0, 25.0],
        "sl_lookback": [1, 3, 5],
        "sl_min_pct": [0.10, 0.15, 0.25],
        "tick_buffer": [0, 2, 4],
        "cooldown_bars": [3, 7, 14],
        "final_rr": [1.0, 1.5, 2.0],
        "trigger_tf_minutes": [3, 5, 7, 10, 15],
    }

    # ------------------------------------------------------------------
    # Simulator settings
    # ------------------------------------------------------------------

    def get_simulator_settings(self, params: Dict[str, Any] = None) -> Dict[str, Any]:
        p = self.get_params(params)
        s = dict(self.simulator_settings)
        # Pine "un trade par fenêtre" tracks TWO slots (fast/slow), each
        # SHARED across long and short — taking a fast long blocks future
        # fast shorts. one_trade_per_window_mtf delegates this Pine-exact
        # semantics to the simulator using the four cross-bar series + the
        # two use-fast flags emitted by generate_signals.
        s["one_trade_per_window_mtf"] = bool(p.get("one_trade_per_window", True))
        # We deliberately leave the v3-style one_trade_per_setup_window OFF
        # (that was the wrong per-side collapse). The two are mutually
        # exclusive in practice.
        s["one_trade_per_setup_window"] = False
        return s

    # ------------------------------------------------------------------
    # Indicator helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _tf_minutes_to_str(m: int) -> str:
        s = _TF_MINUTES_TO_STR.get(int(m))
        if s is None:
            raise ValueError(
                f"GatorMTFv4: unsupported trigger_tf_minutes={m}. "
                f"Supported values: {sorted(_TF_MINUTES_TO_STR.keys())}"
            )
        return s

    @staticmethod
    def _compute_hma_ribbon(
        close: pd.Series,
        ema_len: int,
        hma1_len: int,
        hma2_len: int,
        amp_mult: float,
    ):
        """Compute the amplified HMA ribbon.

        Replicates the Pine block (chart and trigger use identical params)::

            srcEma  = ta.ema(close, emaLen)
            rawHma1 = ta.hma(srcEma, hma1Len)
            rawHma2 = ta.hma(srcEma, hma2Len)
            hma1    = srcEma + (rawHma1 - srcEma) * ampMult
            hma2    = srcEma + (rawHma2 - srcEma) * ampMult
        """
        src_ema = ta.ema(close, length=ema_len)
        raw_h1 = fast_hma(src_ema, hma1_len)
        raw_h2 = fast_hma(src_ema, hma2_len)
        hma1 = src_ema + (raw_h1 - src_ema) * amp_mult
        hma2 = src_ema + (raw_h2 - src_ema) * amp_mult
        return src_ema, hma1, hma2

    @staticmethod
    def _compute_ssl(
        close: pd.Series,
        high: pd.Series,
        low: pd.Series,
        length: int,
        mult: float,
    ):
        """Compute SSL Keltner channel matching Pine::

            BBMC    = ta.wma(2*ta.wma(close, len/2) - ta.wma(close, len),
                             math.round(math.sqrt(len)))
            rangema = ta.ema(ta.tr, len)
            upper   = BBMC + rangema * mult
            lower   = BBMC - rangema * mult
        """
        bbmc = fast_hma_rounded_sqrt(close, length)
        tr = ta.true_range(high, low, close)
        rangema = ta.ema(tr, length=length)
        upper = bbmc + rangema * mult
        lower = bbmc - rangema * mult
        return bbmc, upper, lower

    @staticmethod
    def _compute_osc_sig(
        close: pd.Series,
        high: pd.Series,
        low: pd.Series,
        hl2: pd.Series,
        mL: int,
        sL: int,
    ) -> pd.Series:
        """4Kings oscillator's sig line (no sgD needed for Gator-MTF v4).

        Replicates Pine::

            hi  = ta.highest(mL)            # high
            lo  = ta.lowest(mL)             # low
            av  = ta.sma(hl2, mL)
            rng = hi - lo
            raw = rng != 0 ? (close - avg(hi,lo,av)) / rng * 100 : 0
            sig = ta.ema(ta.linreg(raw, mL, 0), sL)
        """
        hi = high.rolling(window=mL).max()
        lo = low.rolling(window=mL).min()
        av = ta.sma(hl2, length=mL)
        rng = (hi - lo).to_numpy()
        close_np = close.to_numpy()
        avg_np = ((hi + lo + av) / 3.0).to_numpy()
        raw = np.zeros_like(rng)
        nonzero = rng != 0
        raw[nonzero] = (close_np[nonzero] - avg_np[nonzero]) / rng[nonzero] * 100.0
        # Pine: NaN propagates through subsequent ta.linreg / ta.ema.
        nan_any = np.isnan(rng) | np.isnan(close_np) | np.isnan(avg_np)
        raw[nan_any] = np.nan
        linreg = pd.Series(rolling_linreg_last(raw, mL), index=close.index)
        return ta.ema(linreg, length=sL)

    @staticmethod
    def _compute_mfi_smart(
        hl2: pd.Series, volume: pd.Series, mfL: int, mfS: int
    ) -> pd.Series:
        """Smart-Money-Flow MFI centred at 0 — Pine: ``ta.sma(ta.mfi(hl2, mfL) - 50, mfS)``."""
        raw_money_flow = hl2 * volume
        change = hl2.diff()
        positive = raw_money_flow.where(change > 0, 0.0)
        negative = raw_money_flow.where(change < 0, 0.0)
        pos_sum = positive.rolling(window=mfL).sum()
        neg_sum = negative.rolling(window=mfL).sum()
        ratio = pos_sum / (neg_sum + 1e-10)
        mfi_raw = 100.0 - (100.0 / (1.0 + ratio))
        return ta.sma(mfi_raw - 50.0, length=mfS)

    @staticmethod
    def _ta_cross(curr: np.ndarray, ref: np.ndarray) -> np.ndarray:
        """Pine ``ta.cross(a, b)`` — bidirectional cross between bar i-1 and i.

        Equivalent to ``ta.crossover(a,b) or ta.crossunder(a,b)``:
            up   = prev_a <= prev_b AND curr_a >  curr_b
            down = prev_a >= prev_b AND curr_a <  curr_b
        """
        n = curr.size
        if n < 2:
            return np.zeros(n, dtype=bool)
        prev_curr = np.empty_like(curr)
        prev_ref = np.empty_like(ref)
        prev_curr[0] = np.nan
        prev_curr[1:] = curr[:-1]
        prev_ref[0] = np.nan
        prev_ref[1:] = ref[:-1]
        up = (prev_curr <= prev_ref) & (curr > ref)
        down = (prev_curr >= prev_ref) & (curr < ref)
        out = up | down
        nan_any = np.isnan(curr) | np.isnan(ref) | np.isnan(prev_curr) | np.isnan(prev_ref)
        out[nan_any] = False
        return out

    # ------------------------------------------------------------------
    # Signal generation
    # ------------------------------------------------------------------

    def generate_signals(
        self, data: pd.DataFrame, params: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        p = self.get_params(params)

        n = len(data.index)
        if n < 2:
            raise ValueError("GatorMTFv4: not enough bars to backtest.")

        # ---- Validate that the chart is truly M1 ----
        # Use the median bar delta so session gaps and DST transitions don't
        # mislead the check (data.index[1] - data.index[0] is fragile).
        diffs = data.index.to_series().diff().dropna()
        if not diffs.empty:
            median_sec = diffs.dt.total_seconds().median()
            if not 55 <= median_sec <= 65:
                raise ValueError(
                    f"GatorMTFv4 requires M1 chart data (median bar spacing "
                    f"~60s); got {median_sec:.1f}s. Run the backtest with "
                    f"interval='1m'."
                )

        # ---- Reject partial-TP configs we can't faithfully replay ----
        # Default Pine config has partial_rr = hw_partial_pct = 0 (partial off);
        # any combination > 0 would diverge from TradingView in the current
        # engine. Hard-fail so trades never silently mismatch.
        partial_rr = float(p.get("partial_rr", 0.0))
        hw_partial_pct = float(p.get("hw_partial_pct", 0.0))
        if partial_rr > 0.0 and hw_partial_pct > 0.0:
            raise ValueError(
                "GatorMTFv4: partial TP (partial_rr > 0 AND hw_partial_pct > 0) "
                "is not yet supported in the engine — adding it requires an "
                "'intra-bar full exit at TP final with partial as fallback' "
                "mode in the simulator. Set one of partial_rr / hw_partial_pct "
                "to 0 to run; the default config (both 0) matches Pine exactly."
            )

        # ------------------------------------------------------------------
        # 1. Recompose to trigger TF
        # ------------------------------------------------------------------
        trigger_tf_min = int(p["trigger_tf_minutes"])
        trigger_tf = self._tf_minutes_to_str(trigger_tf_min)
        m7 = recompose_bars(
            data[["Open", "High", "Low", "Close", "Volume"]], trigger_tf
        )
        if m7.empty:
            raise ValueError(
                f"GatorMTFv4: recomposed {trigger_tf} dataframe is empty "
                "(insufficient M1 history)."
            )

        # ------------------------------------------------------------------
        # 2. Trigger-TF indicators
        # ------------------------------------------------------------------
        ema_len = int(p["ema_len"])
        hma1_len = int(p["hma1_len"])
        hma2_len = int(p["hma2_len"])
        amp_mult = float(p["amp_mult"])
        ssl_len = int(p["ssl_len"])
        ssl_mult = float(p["ssl_mult"])

        m7_close = m7["Close"]
        m7_high = m7["High"]
        m7_low = m7["Low"]
        _, m7_h1, m7_h2 = self._compute_hma_ribbon(
            m7_close, ema_len, hma1_len, hma2_len, amp_mult
        )
        m7_bbmc, m7_upperk, m7_lowerk = self._compute_ssl(
            m7_close, m7_high, m7_low, ssl_len, ssl_mult
        )

        m7_h1_np = m7_h1.to_numpy()
        m7_h2_np = m7_h2.to_numpy()
        m7_upperk_np = m7_upperk.to_numpy()
        m7_lowerk_np = m7_lowerk.to_numpy()

        # Trigger canal — match Pine: canalRouge = h1 > h2 (strict), canalVert
        # = NOT canalRouge (since the value comes through request.security as
        # canalRougeRaw, and Pine does ``canalVertT = canalRougeRaw == false``).
        m7_canal_rouge = m7_h1_np > m7_h2_np
        m7_canal_rouge[np.isnan(m7_h1_np) | np.isnan(m7_h2_np)] = False
        m7_canal_vert = ~m7_canal_rouge

        # ``ta.cross(h1, upperk) and canalVert_t`` for the long side, etc.
        # canalRouge / canalVert here are evaluated at the CURRENT M7 bar (k),
        # not k-1 — they gate the cross-status of bar k.
        m7_canal_rouge_strict = m7_h1_np > m7_h2_np  # used inline below
        m7_canal_vert_strict = m7_h1_np < m7_h2_np
        nan_strict = np.isnan(m7_h1_np) | np.isnan(m7_h2_np)
        m7_canal_rouge_strict[nan_strict] = False
        m7_canal_vert_strict[nan_strict] = False

        m7_fast_x_upper = self._ta_cross(m7_h1_np, m7_upperk_np)
        m7_fast_x_lower = self._ta_cross(m7_h1_np, m7_lowerk_np)
        m7_slow_x_upper = self._ta_cross(m7_h2_np, m7_upperk_np)
        m7_slow_x_lower = self._ta_cross(m7_h2_np, m7_lowerk_np)

        m7_fast_long_sig = m7_fast_x_upper & m7_canal_vert_strict
        m7_fast_short_sig = m7_fast_x_lower & m7_canal_rouge_strict
        m7_slow_long_sig = m7_slow_x_upper & m7_canal_vert_strict
        m7_slow_short_sig = m7_slow_x_lower & m7_canal_rouge_strict

        # ------------------------------------------------------------------
        # 3. Map trigger values back to M1 (anti-repaint: confirmed = K-1)
        # ------------------------------------------------------------------
        # recompose_bars labels M7 bars at their OPEN time (label='left',
        # closed='left'), so a searchsorted on the M1 timestamps locates the
        # M7 window each M1 bar belongs to.
        m7_open = m7.index
        m7_idx = m7_open.searchsorted(data.index, side="right") - 1
        confirmed_idx = m7_idx - 1
        valid = confirmed_idx >= 0

        # newTriggerBar fires at the first M1 bar of each new M7 window
        # (== Pine's ``timeT != timeT[1]``: the confirmed M7 bar just changed).
        new_trigger_bar = np.zeros(n, dtype=bool)
        new_trigger_bar[1:] = m7_idx[1:] != m7_idx[:-1]

        canal_rouge_T = np.zeros(n, dtype=bool)
        canal_vert_T = np.zeros(n, dtype=bool)
        fast_long_sig_t = np.zeros(n, dtype=bool)
        fast_short_sig_t = np.zeros(n, dtype=bool)
        slow_long_sig_t = np.zeros(n, dtype=bool)
        slow_short_sig_t = np.zeros(n, dtype=bool)
        hma1_t_arr = np.full(n, np.nan)
        hma2_t_arr = np.full(n, np.nan)
        ssl_up_t_arr = np.full(n, np.nan)
        ssl_lo_t_arr = np.full(n, np.nan)
        ssl_base_t_arr = np.full(n, np.nan)

        valid_indices = np.where(valid)[0]
        if valid_indices.size > 0:
            cidx = confirmed_idx[valid_indices]
            canal_rouge_T[valid_indices] = m7_canal_rouge[cidx]
            # Pine: canalVertT = canalRougeRaw == false (so NaN-driven values
            # land in vert; matches what request.security returns initially).
            canal_vert_T[valid_indices] = m7_canal_vert[cidx]
            fast_long_sig_t[valid_indices] = m7_fast_long_sig[cidx]
            fast_short_sig_t[valid_indices] = m7_fast_short_sig[cidx]
            slow_long_sig_t[valid_indices] = m7_slow_long_sig[cidx]
            slow_short_sig_t[valid_indices] = m7_slow_short_sig[cidx]
            hma1_t_arr[valid_indices] = m7_h1_np[cidx]
            hma2_t_arr[valid_indices] = m7_h2_np[cidx]
            ssl_up_t_arr[valid_indices] = m7_upperk_np[cidx]
            ssl_lo_t_arr[valid_indices] = m7_lowerk_np[cidx]
            ssl_base_t_arr[valid_indices] = m7_bbmc.to_numpy()[cidx]

        # Edge triggers fire ONCE per new M7 window, on the first M1 bar of
        # that window.
        fast_cross_long = new_trigger_bar & fast_long_sig_t
        fast_cross_short = new_trigger_bar & fast_short_sig_t
        slow_cross_long = new_trigger_bar & slow_long_sig_t
        slow_cross_short = new_trigger_bar & slow_short_sig_t

        # ------------------------------------------------------------------
        # 4. Track last cross bar (M1 chart bar index) + windows
        # ------------------------------------------------------------------
        arange = np.arange(n, dtype=np.int64)

        def _last_true_bar(mask: np.ndarray) -> np.ndarray:
            """For each i, return the largest j <= i with mask[j] True (or -1)."""
            tagged = np.where(mask, arange, -1)
            return np.maximum.accumulate(tagged)

        last_fast_long_cross_bar = _last_true_bar(fast_cross_long)
        last_fast_short_cross_bar = _last_true_bar(fast_cross_short)
        last_slow_long_cross_bar = _last_true_bar(slow_cross_long)
        last_slow_short_cross_bar = _last_true_bar(slow_cross_short)

        # Entry window length in chart bars (Pine: ceil(entry_bars * tfRatio)).
        chart_seconds = 60
        trigger_seconds = trigger_tf_min * 60
        tf_ratio = max(1.0, trigger_seconds / chart_seconds)
        window_bars_chart = max(
            1, int(round(int(p["entry_window_bars_trigger"]) * tf_ratio))
        )

        window_fast_long = (last_fast_long_cross_bar >= 0) & (
            (arange - last_fast_long_cross_bar) <= window_bars_chart
        )
        window_fast_short = (last_fast_short_cross_bar >= 0) & (
            (arange - last_fast_short_cross_bar) <= window_bars_chart
        )
        window_slow_long = (last_slow_long_cross_bar >= 0) & (
            (arange - last_slow_long_cross_bar) <= window_bars_chart
        )
        window_slow_short = (last_slow_short_cross_bar >= 0) & (
            (arange - last_slow_short_cross_bar) <= window_bars_chart
        )
        window_long = window_fast_long | window_slow_long
        window_short = window_fast_short | window_slow_short

        # ------------------------------------------------------------------
        # 5. M1 indicators
        # ------------------------------------------------------------------
        close = data["Close"]
        high = data["High"]
        low = data["Low"]
        volume = data["Volume"]
        hl2 = (high + low) / 2.0

        _, m1_h1, m1_h2 = self._compute_hma_ribbon(
            close, ema_len, hma1_len, hma2_len, amp_mult
        )
        m1_h1_np = m1_h1.to_numpy()
        m1_h2_np = m1_h2.to_numpy()
        m1_canal_rouge = m1_h1_np > m1_h2_np
        m1_canal_vert = m1_h1_np < m1_h2_np
        nan_m1 = np.isnan(m1_h1_np) | np.isnan(m1_h2_np)
        m1_canal_rouge[nan_m1] = False
        m1_canal_vert[nan_m1] = False

        mfi = self._compute_mfi_smart(
            hl2, volume, int(p["mf_length"]), int(p["mf_smooth"])
        )
        mfi_np = mfi.to_numpy()
        osc_bull = mfi_np > 0
        osc_bear = mfi_np < 0
        osc_bull[np.isnan(mfi_np)] = False
        osc_bear[np.isnan(mfi_np)] = False

        sig_threshold = float(p["sig_extreme_threshold"])
        osc_sig = self._compute_osc_sig(
            close, high, low, hl2,
            int(p["hyper_wave_length"]), int(p["signal_length"]),
        )
        osc_sig_np = osc_sig.to_numpy()
        sig_extreme_bull = osc_sig_np >= sig_threshold
        sig_extreme_bear = osc_sig_np <= -sig_threshold
        sig_extreme_bull[np.isnan(osc_sig_np)] = False
        sig_extreme_bear[np.isnan(osc_sig_np)] = False

        # ------------------------------------------------------------------
        # 6. Cases A / B / C / D — armed + entry flags
        # ------------------------------------------------------------------
        case_a_on = bool(p["case_a_on"])
        case_b_on = bool(p["case_b_on"])
        case_c_on = bool(p["case_c_on"])
        case_d_on = bool(p["case_d_on"])

        armed_a_long = window_long & canal_vert_T & m1_canal_vert & osc_bull
        armed_b_long = window_long & canal_vert_T & m1_canal_vert & osc_bear
        armed_c_long = window_long & canal_rouge_T & m1_canal_vert & osc_bear
        armed_d_long = window_long & canal_rouge_T & m1_canal_vert & osc_bull

        armed_a_short = window_short & canal_rouge_T & m1_canal_rouge & osc_bear
        armed_b_short = window_short & canal_rouge_T & m1_canal_rouge & osc_bull
        armed_c_short = window_short & canal_vert_T & m1_canal_rouge & osc_bull
        armed_d_short = window_short & canal_vert_T & m1_canal_rouge & osc_bear

        zero = np.zeros(n, dtype=bool)
        entry_a_long = armed_a_long if case_a_on else zero
        entry_b_long = armed_b_long if case_b_on else zero
        entry_c_long = (armed_c_long & sig_extreme_bear) if case_c_on else zero
        entry_d_long = (armed_d_long & sig_extreme_bear) if case_d_on else zero
        long_signal_raw = (
            entry_a_long | entry_b_long | entry_c_long | entry_d_long
        )

        entry_a_short = armed_a_short if case_a_on else zero
        entry_b_short = armed_b_short if case_b_on else zero
        entry_c_short = (armed_c_short & sig_extreme_bull) if case_c_on else zero
        entry_d_short = (armed_d_short & sig_extreme_bull) if case_d_on else zero
        short_signal_raw = (
            entry_a_short | entry_b_short | entry_c_short | entry_d_short
        )

        # ------------------------------------------------------------------
        # 7. SL + TP (final)
        # ------------------------------------------------------------------
        tick_size = float(p["tick_size"])
        sl_buffer = int(p["tick_buffer"]) * tick_size
        sl_lookback = max(1, int(p["sl_lookback"]))
        sl_min_pct = float(p["sl_min_pct"])
        final_rr = float(p["final_rr"])

        low_np = low.to_numpy()
        high_np = high.to_numpy()
        close_np = close.to_numpy()

        if sl_lookback == 1:
            lowest_low = low_np
            highest_high = high_np
        else:
            lowest_low = pd.Series(low_np).rolling(sl_lookback).min().to_numpy()
            highest_high = pd.Series(high_np).rolling(sl_lookback).max().to_numpy()

        raw_sl_long = lowest_low - sl_buffer
        raw_sl_short = highest_high + sl_buffer

        min_sl_dist = close_np * (sl_min_pct / 100.0)
        min_sl_long_floor = close_np - min_sl_dist
        min_sl_short_floor = close_np + min_sl_dist

        # Pine: SL = min %-floor when raw SL is closer than the floor, else raw.
        calc_sl_long = np.where(
            raw_sl_long > min_sl_long_floor, min_sl_long_floor, raw_sl_long
        )
        calc_sl_short = np.where(
            raw_sl_short < min_sl_short_floor, min_sl_short_floor, raw_sl_short
        )

        def _round_tick(arr: np.ndarray) -> np.ndarray:
            if tick_size > 0:
                return np.round(arr / tick_size) * tick_size
            return arr

        sl_long_rounded = _round_tick(calc_sl_long)
        sl_short_rounded = _round_tick(calc_sl_short)
        entry_long_rounded = _round_tick(close_np)
        entry_short_rounded = _round_tick(close_np)

        risk_long = entry_long_rounded - sl_long_rounded
        risk_short = sl_short_rounded - entry_short_rounded
        tp_final_long = _round_tick(entry_long_rounded + risk_long * final_rr)
        tp_final_short = _round_tick(entry_short_rounded - risk_short * final_rr)

        # Pine: ``slLongOk = calcStopLong < close``. SL must be strictly on the
        # other side of close — guards against zero-distance entries.
        sl_long_ok = sl_long_rounded < close_np
        sl_short_ok = sl_short_rounded > close_np

        long_signal = long_signal_raw & sl_long_ok
        short_signal = short_signal_raw & sl_short_ok

        # ------------------------------------------------------------------
        # 8. One-trade-per-window (Pine semantics: per-family, NOT per-side)
        # ------------------------------------------------------------------
        # Each fenêtre family (fast / slow) has ONE slot shared between long
        # and short — taking a fast long locks fast for subsequent fast
        # SHORTS too until a new fast cross fires on BOTH sides. We delegate
        # the gating to the simulator (`one_trade_per_window_mtf`) and just
        # provide:
        #   - the 4 cross-bar series (latest cross bar per family/side)
        #   - the 2 use_fast_for_{long,short} flags (Pine: useFastForLong =
        #     windowFastLong, regardless of slow window)
        # Sentinel -1 ≡ Pine's `na` (no cross fired yet).
        use_fast_for_long_series = window_fast_long
        use_fast_for_short_series = window_fast_short

        # ------------------------------------------------------------------
        # 9. Build the signals dict for the simulator
        # ------------------------------------------------------------------
        idx = data.index
        sl_long_series = np.where(long_signal, sl_long_rounded, np.nan)
        sl_short_series = np.where(short_signal, sl_short_rounded, np.nan)
        tp_long_series = np.where(long_signal, tp_final_long, np.nan)
        tp_short_series = np.where(short_signal, tp_final_short, np.nan)

        debug_frame = pd.DataFrame(
            {
                "Open": data["Open"],
                "High": high,
                "Low": low,
                "Close": close,
                # M1 indicators
                "m1_hma1": m1_h1,
                "m1_hma2": m1_h2,
                "m1_canal_rouge": m1_canal_rouge.astype(int),
                "m1_canal_vert": m1_canal_vert.astype(int),
                "mfi": mfi,
                "osc_sig": osc_sig,
                "osc_bull": osc_bull.astype(int),
                "osc_bear": osc_bear.astype(int),
                "sig_extreme_bull": sig_extreme_bull.astype(int),
                "sig_extreme_bear": sig_extreme_bear.astype(int),
                # Trigger values mapped to M1 (confirmed = K-1)
                "trigger_window_idx": m7_idx,
                "confirmed_trigger_idx": confirmed_idx,
                "new_trigger_bar": new_trigger_bar.astype(int),
                "hma1_T": hma1_t_arr,
                "hma2_T": hma2_t_arr,
                "ssl_base_T": ssl_base_t_arr,
                "ssl_up_T": ssl_up_t_arr,
                "ssl_lo_T": ssl_lo_t_arr,
                "canal_rouge_T": canal_rouge_T.astype(int),
                "canal_vert_T": canal_vert_T.astype(int),
                "fast_long_sig_T": fast_long_sig_t.astype(int),
                "fast_short_sig_T": fast_short_sig_t.astype(int),
                "slow_long_sig_T": slow_long_sig_t.astype(int),
                "slow_short_sig_T": slow_short_sig_t.astype(int),
                "fast_cross_long": fast_cross_long.astype(int),
                "fast_cross_short": fast_cross_short.astype(int),
                "slow_cross_long": slow_cross_long.astype(int),
                "slow_cross_short": slow_cross_short.astype(int),
                "window_fast_long": window_fast_long.astype(int),
                "window_fast_short": window_fast_short.astype(int),
                "window_slow_long": window_slow_long.astype(int),
                "window_slow_short": window_slow_short.astype(int),
                # Cases
                "armed_A_long": armed_a_long.astype(int),
                "armed_B_long": armed_b_long.astype(int),
                "armed_C_long": armed_c_long.astype(int),
                "armed_D_long": armed_d_long.astype(int),
                "armed_A_short": armed_a_short.astype(int),
                "armed_B_short": armed_b_short.astype(int),
                "armed_C_short": armed_c_short.astype(int),
                "armed_D_short": armed_d_short.astype(int),
                # Final entries
                "long_entry": long_signal.astype(int),
                "short_entry": short_signal.astype(int),
                "sl_long": sl_long_rounded,
                "sl_short": sl_short_rounded,
                "tp_final_long": tp_final_long,
                "tp_final_short": tp_final_short,
                # MTF per-family one-trade-per-window inputs (debug-visible)
                "last_fast_long_cross_bar": last_fast_long_cross_bar,
                "last_fast_short_cross_bar": last_fast_short_cross_bar,
                "last_slow_long_cross_bar": last_slow_long_cross_bar,
                "last_slow_short_cross_bar": last_slow_short_cross_bar,
                "use_fast_for_long": use_fast_for_long_series.astype(int),
                "use_fast_for_short": use_fast_for_short_series.astype(int),
                "param_window_bars_chart": window_bars_chart,
                "param_trigger_tf_min": trigger_tf_min,
            },
            index=idx,
        )

        return {
            "long_entries": pd.Series(long_signal, index=idx),
            "short_entries": pd.Series(short_signal, index=idx),
            "sl_long": pd.Series(sl_long_series, index=idx),
            "sl_short": pd.Series(sl_short_series, index=idx),
            "tp1_long": pd.Series(tp_long_series, index=idx),
            "tp1_short": pd.Series(tp_short_series, index=idx),
            # ema_main / ema_secondary are required keys but never consumed:
            # tp1_full_exit closes the position before any EMA-cross check,
            # and ema_exit_after_tp1_only gates the close-based path anyway.
            "ema_main": pd.Series(np.nan, index=idx),
            "ema_secondary": pd.Series(np.nan, index=idx),
            "cooldown_bars": int(p["cooldown_bars"]),
            # MTF per-family "un trade par fenêtre" — consumed by the
            # simulator when `one_trade_per_window_mtf=True`.
            "last_fast_long_cross_bar": pd.Series(last_fast_long_cross_bar, index=idx),
            "last_fast_short_cross_bar": pd.Series(last_fast_short_cross_bar, index=idx),
            "last_slow_long_cross_bar": pd.Series(last_slow_long_cross_bar, index=idx),
            "last_slow_short_cross_bar": pd.Series(last_slow_short_cross_bar, index=idx),
            "use_fast_for_long": pd.Series(use_fast_for_long_series, index=idx),
            "use_fast_for_short": pd.Series(use_fast_for_short_series, index=idx),
            "debug_frame": debug_frame,
        }
