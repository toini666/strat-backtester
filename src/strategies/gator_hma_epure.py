"""
Gator HMA Epure strategy.

Translated from PineScript indicator Gator-HMA-Epure.txt.

Entry conditions mirror the PineScript exactly:
  - HMA canal direction
  - Smart Money Flow slope over 2 bars
  - Keltner channel span/close condition
  - OCC higher-timeframe direction (non-repaint, lookahead_off)
  - Keltner basis position

Exit logic for the backtester:
  - Fixed stop loss in points from entry
  - Single fixed TP1 in points, executed as a full exit on touch
  - Auto-close remains handled by engine settings
"""

from __future__ import annotations

import math
from typing import Any, Dict, Tuple

import numpy as np
import pandas as pd
import pandas_ta_classic as ta

from .base import Strategy
from .hma_ssl_osci import HMASSLOsci

import warnings

warnings.filterwarnings("ignore", category=FutureWarning, module="pandas_ta_classic")


class GatorHMAEpure(Strategy):
    """Gator HMA Epure with fixed-point SL/TP and non-repaint OCC filter."""

    name = "GatorHMAEpure"
    manual_exit = True
    use_simulator = True
    blackout_sensitive = True
    simulator_settings = {
        "tp1_execution_mode": "touch",
    }

    default_params = {
        # HMA canal
        "ema_len": 13,
        "hma1_len": 13,
        "hma2_len": 21,
        "amp_mult": 2.0,
        # Gator Keltner
        "src1_len": 7,
        "length1": 60,
        "mult1_p": 1.0,
        "mult1_atr": 0.2,
        "use_smooth1": False,
        "type_smooth1": "EMA",
        "len_smooth1": 3,
        # OCC
        "basis_len_occ": 8,
        "multiplier_occ": False,  # False => x7, True => x3
        # Smart Money Flow
        "mf_length": 35,
        "mf_smooth": 6,
        # Risk
        "sl_points": 80.0,
        "tp1_points": 40.0,
        "cooldown_bars": 0,
        # Injected by engine
        "tick_size": 0.25,
    }

    param_ranges = {
        "ema_len": [9, 13, 21],
        "hma1_len": [9, 13, 21],
        "hma2_len": [13, 21, 34],
        "amp_mult": [1.5, 2.0, 2.5],
        "src1_len": [5, 7, 9],
        "length1": [40, 60, 80],
        "mult1_p": [0.8, 1.0, 1.2],
        "mult1_atr": [0.1, 0.2, 0.3],
        "basis_len_occ": [5, 8, 13],
        "mf_length": [25, 35, 45],
        "mf_smooth": [4, 6, 8],
        "sl_points": [40.0, 60.0, 80.0, 100.0],
        "tp1_points": [20.0, 30.0, 40.0, 50.0],
    }

    def get_simulator_settings(self, params=None):
        p = self.get_params(params)
        settings = self.simulator_settings.copy()
        settings["tp1_full_exit"] = True
        settings["tp1_partial_pct"] = 1.0
        settings["tp2_partial_pct"] = 0.0
        settings["cooldown_bars"] = p.get("cooldown_bars", 0)
        return settings

    @staticmethod
    def _round_half_up(value: float) -> int:
        return int(math.floor(value + 0.5))

    @staticmethod
    def _round_tick(price: float, tick_size: float) -> float:
        if tick_size > 0:
            return round(price / tick_size) * tick_size
        return price

    @staticmethod
    def _apply_ma(ma_type: str, series: pd.Series, length: int) -> pd.Series:
        if ma_type == "SMA":
            return ta.sma(series, length=length)
        if ma_type == "EMA":
            return ta.ema(series, length=length)
        if ma_type == "WMA":
            return ta.wma(series, length=length)
        if ma_type == "RMA":
            return ta.rma(series, length=length)
        raise ValueError(f"Unsupported smoothing type: {ma_type}")

    @staticmethod
    def _compute_occ_non_repaint(
        open_: pd.Series,
        close: pd.Series,
        basis_len: int,
        factor: int,
    ) -> Tuple[pd.Series, pd.Series]:
        """Replicate request.security(..., lookahead_off) on factor× chart timeframe."""
        if factor <= 0:
            raise ValueError("factor must be positive")

        index = close.index
        if len(index) == 0:
            empty = pd.Series(dtype=float, index=index)
            return empty, empty

        diffs = index.to_series().diff()
        session_ids = (diffs > pd.Timedelta(minutes=30)).cumsum()

        htf_open_vals = []
        htf_close_vals = []
        htf_last_idx = []

        for _, segment_index in index.to_series().groupby(session_ids):
            seg_idx = segment_index.index
            full_groups = len(seg_idx) // factor
            for group_id in range(full_groups):
                start = group_id * factor
                end = start + factor
                chunk_idx = seg_idx[start:end]
                htf_open_vals.append(float(open_.loc[chunk_idx[0]]))
                htf_close_vals.append(float(close.loc[chunk_idx[-1]]))
                htf_last_idx.append(chunk_idx[-1])

        if not htf_last_idx:
            nan_series = pd.Series(np.nan, index=index)
            return nan_series, nan_series

        htf_df = pd.DataFrame(
            {
                "Open": htf_open_vals,
                "Close": htf_close_vals,
            },
            index=pd.DatetimeIndex(htf_last_idx),
        )
        open_alt = ta.rma(htf_df["Open"], length=basis_len)
        close_alt = ta.rma(htf_df["Close"], length=basis_len)

        open_aligned = open_alt.reindex(index).ffill()
        close_aligned = close_alt.reindex(index).ffill()
        return close_aligned, open_aligned

    def generate_signals(
        self, data: pd.DataFrame, params: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        p = self.get_params(params)

        tick_size = p["tick_size"]
        close = data["Close"]
        open_ = data["Open"]
        high = data["High"]
        low = data["Low"]
        hl2 = (high + low) / 2.0

        _, hma1, hma2, _, _, canal_green = HMASSLOsci._compute_hma_canal_full(
            close,
            p["ema_len"],
            p["hma1_len"],
            p["hma2_len"],
            p["amp_mult"],
        )

        eff_len1 = max(1, self._round_half_up(p["length1"] * p["mult1_p"]))
        src1_ema = ta.ema(close, length=p["src1_len"])
        ma1_base = ta.ema(src1_ema, length=eff_len1)
        ma1 = (
            self._apply_ma(p["type_smooth1"], ma1_base, p["len_smooth1"])
            if p["use_smooth1"]
            else ma1_base
        )
        atr_200 = ta.atr(high, low, close, length=200)
        up1_raw = ma1 + atr_200 * p["mult1_atr"]
        lo1_raw = ma1 - atr_200 * p["mult1_atr"]

        occ_factor = 3 if p["multiplier_occ"] else 7
        close_occ_alt, open_occ_alt = self._compute_occ_non_repaint(
            open_,
            close,
            p["basis_len_occ"],
            occ_factor,
        )

        current_mfi = HMASSLOsci._compute_mfi(
            hl2,
            data["Volume"],
            p["mf_length"],
            p["mf_smooth"],
        )

        c_hma_sh = (hma1 < hma2).fillna(False)
        c_p8_sh = (current_mfi <= current_mfi.shift(2)).fillna(False)
        c_ssl_sh = ((high >= lo1_raw) & (close <= up1_raw)).fillna(False)
        c_ser_sh = (close_occ_alt < open_occ_alt).fillna(False)
        c_gs_sh = (ma1 > close).fillna(False)

        c_hma_lo = canal_green.fillna(False)
        c_p8_lo = (current_mfi >= current_mfi.shift(2)).fillna(False)
        c_ssl_lo = ((low <= lo1_raw) & (close >= up1_raw)).fillna(False)
        c_ser_lo = (close_occ_alt > open_occ_alt).fillna(False)
        c_gs_lo = (ma1 < close).fillna(False)

        long_entries = (c_hma_lo & c_p8_lo & c_ssl_lo & c_ser_lo & c_gs_lo).fillna(False)
        short_entries = (c_hma_sh & c_p8_sh & c_ssl_sh & c_ser_sh & c_gs_sh).fillna(False)

        n = len(data)
        sl_long = np.full(n, np.nan)
        sl_short = np.full(n, np.nan)
        tp1_long = np.full(n, np.nan)
        tp1_short = np.full(n, np.nan)
        entry_price_long = np.full(n, np.nan)
        entry_price_short = np.full(n, np.nan)

        sl_points = p["sl_points"]
        tp1_points = p["tp1_points"]
        rounded_close = close.apply(lambda v: self._round_tick(v, tick_size))

        long_idx = np.flatnonzero(long_entries.values)
        for i in long_idx:
            entry = rounded_close.iloc[i]
            entry_price_long[i] = entry
            sl_long[i] = self._round_tick(entry - sl_points, tick_size)
            if tp1_points > 0:
                tp1_long[i] = self._round_tick(entry + tp1_points, tick_size)

        short_idx = np.flatnonzero(short_entries.values)
        for i in short_idx:
            entry = rounded_close.iloc[i]
            entry_price_short[i] = entry
            sl_short[i] = self._round_tick(entry + sl_points, tick_size)
            if tp1_points > 0:
                tp1_short[i] = self._round_tick(entry - tp1_points, tick_size)

        nan_series = pd.Series(np.nan, index=data.index)
        debug_frame = pd.DataFrame(
            {
                "Open": open_,
                "High": high,
                "Low": low,
                "Close": close,
                "hma1": hma1,
                "hma2": hma2,
                "canal_green": canal_green.astype(float),
                "kc_basis": ma1,
                "kc_upper": up1_raw,
                "kc_lower": lo1_raw,
                "occ_close_alt": close_occ_alt,
                "occ_open_alt": open_occ_alt,
                "mfi": current_mfi,
                "c_hma_lo": c_hma_lo.astype(int),
                "c_p8_lo": c_p8_lo.astype(int),
                "c_ssl_lo": c_ssl_lo.astype(int),
                "c_ser_lo": c_ser_lo.astype(int),
                "c_gs_lo": c_gs_lo.astype(int),
                "c_hma_sh": c_hma_sh.astype(int),
                "c_p8_sh": c_p8_sh.astype(int),
                "c_ssl_sh": c_ssl_sh.astype(int),
                "c_ser_sh": c_ser_sh.astype(int),
                "c_gs_sh": c_gs_sh.astype(int),
                "long_entry_signal": long_entries.astype(int),
                "short_entry_signal": short_entries.astype(int),
                "sl_long": sl_long,
                "sl_short": sl_short,
                "tp1_long": tp1_long,
                "tp1_short": tp1_short,
            },
            index=data.index,
        )

        return {
            "long_entries": pd.Series(long_entries.values, index=data.index),
            "short_entries": pd.Series(short_entries.values, index=data.index),
            "sl_long": pd.Series(sl_long, index=data.index),
            "sl_short": pd.Series(sl_short, index=data.index),
            "tp1_long": pd.Series(tp1_long, index=data.index),
            "tp1_short": pd.Series(tp1_short, index=data.index),
            "entry_price_long": pd.Series(entry_price_long, index=data.index),
            "entry_price_short": pd.Series(entry_price_short, index=data.index),
            "ema_main": nan_series,
            "ema_secondary": nan_series,
            "cooldown_bars": p["cooldown_bars"],
            "debug_frame": debug_frame,
        }
