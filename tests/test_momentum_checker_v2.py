"""
Tests for MomentumCheckerV2:
  * generate_signals runs without error and returns the expected keys
  * V2 with new params disabled reproduces V1 entry signals bit-for-bit
    (V1 Rob Reversal toggled off — V2 dropped that module per V2 Pine)
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.strategies.momentum_checker import MomentumChecker  # noqa: E402
from src.strategies.momentum_checker_v2 import MomentumCheckerV2  # noqa: E402


def _make_data(n_bars: int = 800, seed: int = 7) -> pd.DataFrame:
    """Synthetic 7-minute OHLCV series long enough to clear warmup."""
    rng = np.random.default_rng(seed)
    base = 20000.0
    # Mix of trends and chops to exercise scoring on both sides.
    returns = rng.normal(0.0, 0.0009, size=n_bars)
    trend_phase = np.sin(np.linspace(0, 6 * np.pi, n_bars)) * 0.0006
    close = base * np.cumprod(1 + returns + trend_phase)

    open_ = np.empty_like(close)
    open_[0] = base
    open_[1:] = close[:-1]
    body = np.abs(close - open_)
    wick = body + np.abs(rng.normal(0.0, 4.0, size=n_bars))
    high = np.maximum(open_, close) + wick
    low = np.minimum(open_, close) - wick
    volume = rng.integers(1000, 20000, size=n_bars).astype(np.int64)

    idx = pd.date_range("2025-01-01 00:00", periods=n_bars, freq="7min", tz="UTC")
    df = pd.DataFrame(
        {
            "Open": open_,
            "High": high,
            "Low": low,
            "Close": close,
            "Volume": volume,
        },
        index=idx,
    )
    df["is_blackout"] = False
    return df


def _shared_params() -> dict:
    """Param set shared by V1 and V2 for the reproduction test.

    Uses V1-Pine defaults (which differ from V1 Python defaults — see
    CLAUDE.md). All filter toggles are explicit on both sides so the
    scoring-style change in V2 (toggle-off removes the bonus) doesn't
    introduce a phantom divergence.
    """
    return {
        # Core scoring/risk
        "long_threshold":  4,
        "short_threshold": 4,
        "min_gap":         2,
        "max_candle_pct":  5.0,  # generous so we actually get entries
        "sl_lookback":     5,
        "sl_max_points":   200.0,
        "rr_tp":           2.0,
        "tick_buffer":     0,

        # Oscillator (V1 Pine defaults)
        "hyper_wave_length":     5,
        "signal_type":           "SMA",
        "signal_length":         3,
        "mf_length":             35,
        "mf_smooth":             5,
        "hw_filter_on":          True,
        "hw_level":              16.0,
        "hw_extreme_filter_on":  True,
        "sig_extreme_filter_on": False,
        "hw_extreme":            20.0,
        # EMAs
        "ema_prin_len": 30,
        "ema_sec_len":  20,
        # Supertrend
        "st_atr":  14,
        "st_mult": 3.0,
        # UT Bot
        "ut_key":        1.0,
        "ut_atr_period": 10,
        # STC
        "stc_length":    12,
        "stc_fast_len":  26,
        "stc_slow_len":  50,
        # HMA
        "hma_ema_len": 7,
        "hma1_len":    42,
        "hma2_len":    84,
        "amp_mult":    2.5,
    }


def _v1_params(shared: dict) -> dict:
    p = {**MomentumChecker.default_params, **shared}
    # V1 has Rob Reversal — disable for a fair comparison (V2 dropped it).
    p["rob_on"] = False
    p["pts_rob"] = 0
    # V1 uses Heikin Ashi flag — V2 has none, default off.
    p["use_heikin_ashi"] = False
    return p


def _v2_params_v1_compat(shared: dict) -> dict:
    p = {**MomentumCheckerV2.default_params, **shared}
    # New-in-V2 toggles set to V1-equivalent.
    p["cloud_filter_on"] = True
    p["delta_filter_on"] = True
    p["cloud_zero_filter_on"] = False
    p["pts_cloud_zero"] = 0
    p["delta_off_mode"] = "both"
    p["sig_extreme"] = shared["hw_extreme"]
    p["hma_pol_bars"] = -1     # disables polarity tolerance → V1 strict canalGreen
    p["pts_hma_slow"] = 0       # neutralise the SSL-cross bucket
    p["hma_window_bars"] = 0
    p["be_at_rr"] = 0.0
    return p


# ----------------------------------------------------------------------
# Smoke test
# ----------------------------------------------------------------------

def test_v2_signals_smoke():
    data = _make_data()
    strat = MomentumCheckerV2()
    s = strat.generate_signals(data)
    for key in (
        "long_entries", "short_entries", "sl_long", "sl_short",
        "tp1_long", "tp1_short", "be_long", "be_short",
        "ema_main", "ema_secondary", "cooldown_bars", "debug_frame",
    ):
        assert key in s, f"missing key {key}"
    assert isinstance(s["long_entries"], pd.Series)
    assert len(s["long_entries"]) == len(data)
    # The synthetic series should produce *some* signals; otherwise the
    # downstream V1≈V2 test would pass trivially.
    assert int(s["long_entries"].sum() + s["short_entries"].sum()) > 0


# ----------------------------------------------------------------------
# BE@RR: when be_at_rr > 0 we populate be_long / be_short at entries.
# ----------------------------------------------------------------------

def test_v2_be_at_rr_populates_be_series():
    data = _make_data()
    strat = MomentumCheckerV2()
    params = {**MomentumCheckerV2.default_params}
    params["max_candle_pct"] = 5.0
    params["min_gap"] = 2
    params["long_threshold"] = 4
    params["short_threshold"] = 4
    params["be_at_rr"] = 1.0
    s = strat.generate_signals(data, params)
    long_entry_idx = np.where(s["long_entries"].values)[0]
    short_entry_idx = np.where(s["short_entries"].values)[0]
    if len(long_entry_idx) == 0 and len(short_entry_idx) == 0:
        pytest.skip("no signals on this slice — skip BE check")
    be_l = s["be_long"].values
    be_s = s["be_short"].values
    for i in long_entry_idx:
        assert not np.isnan(be_l[i]), f"long entry at {i} should have a BE level"
    for i in short_entry_idx:
        assert not np.isnan(be_s[i]), f"short entry at {i} should have a BE level"


# ----------------------------------------------------------------------
# V1 ≈ V2: same entry signals when V2's new params are disabled.
# ----------------------------------------------------------------------

def test_v2_reproduces_v1_when_new_params_disabled():
    data = _make_data()
    shared = _shared_params()
    v1_p = _v1_params(shared)
    v2_p = _v2_params_v1_compat(shared)

    v1 = MomentumChecker()
    v2 = MomentumCheckerV2()
    s1 = v1.generate_signals(data, v1_p)
    s2 = v2.generate_signals(data, v2_p)

    le1 = s1["long_entries"].values.astype(bool)
    le2 = s2["long_entries"].values.astype(bool)
    se1 = s1["short_entries"].values.astype(bool)
    se2 = s2["short_entries"].values.astype(bool)

    # Diagnostics if they don't match: surface where & how many bars diverge.
    if not (np.array_equal(le1, le2) and np.array_equal(se1, se2)):
        diff_long_idx = np.where(le1 != le2)[0]
        diff_short_idx = np.where(se1 != se2)[0]
        df = s1["debug_frame"]
        df2 = s2["debug_frame"]
        rows = []
        for i in list(diff_long_idx[:5]) + list(diff_short_idx[:5]):
            rows.append(
                f"bar={i} v1_long={int(le1[i])} v2_long={int(le2[i])}  "
                f"v1_short={int(se1[i])} v2_short={int(se2[i])}  "
                f"v1_pts_L/S={df['pts_long'].iloc[i]}/{df['pts_short'].iloc[i]}  "
                f"v2_pts_L/S={df2['pts_long'].iloc[i]}/{df2['pts_short'].iloc[i]}"
            )
        diag = "\n".join(rows)
        pytest.fail(
            f"V1/V2 entry mismatch — long diff={len(diff_long_idx)} "
            f"short diff={len(diff_short_idx)}\n{diag}"
        )

    # Also assert SL/TP prices line up where entries fire.
    entry_mask = le1 | se1
    for key in ("sl_long", "sl_short", "tp1_long", "tp1_short"):
        a1 = s1[key].values
        a2 = s2[key].values
        for i in np.where(entry_mask)[0]:
            if np.isnan(a1[i]) and np.isnan(a2[i]):
                continue
            assert np.isfinite(a1[i]) and np.isfinite(a2[i])
            assert abs(a1[i] - a2[i]) < 1e-6, (
                f"{key} diverges at bar {i}: v1={a1[i]} v2={a2[i]}"
            )
