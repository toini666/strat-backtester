"""Campaign constants for 2026-05-20 MomentumCheckerV2 MGC 7m.

Mirror of the v2 MNQ campaign but applied to MGC.

Goal:
  - Anchor: V1 MGC preset "New base MomentumChecker — MGC 7m — WINNER"
    (PnL $56.4k / DD $2.43k *as reported with the buggy DD metric*).
  - Hard ceiling (user constraint): $DD ≤ $2,500
  - Soft target  (user constraint): $DD ≤ $2,000
  - Maximise PnL within the hard ceiling. Prefer configs under the soft
    target if PnL is close.

Fixed by user constraint:
  - symbol  = MGC
  - tf      = 7m
  - period  = 2025-01-07 → 2026-05-15
  - max contracts = 20
  - no daily win/loss limits
  - auto_close = 22:00 (CME close, reference Brussels)

V1 → V2 translation notes:
  - V2 removed Rob Reversal. V1 MGC had `rob_on=True, pts_rob=1`, so V2
    cannot replicate V1 entries exactly. The V1-compat baseline will
    differ from V1 numbers — that's expected.
  - delta_off_mode="both" + sig_extreme=hw_extreme + cloud_zero_off
    + hma_pol_bars=-1 + pts_hma_slow=0 + hma_window_bars=0
    + be_at_rr=0.0 = V1-compat for the modules V2 kept.
"""

from __future__ import annotations

STRATEGY = "MomentumCheckerV2"
SYMBOL = "MGC"
INTERVAL = "7m"

START = "2025-01-07T00:00"
END   = "2026-05-15T22:59"

INITIAL_EQUITY = 50_000.0
MAX_CONTRACTS = 20

# V1 MGC anchor's risk
RISK_PER_TRADE = 0.006   # 0.6%

# User-stated DD constraints
DD_CEILING = 2_500.0
DD_TARGET  = 2_000.0

# V1 MGC anchor metrics (as stored — pre-patch, % × initial = $2,370 ≈ $2.43k)
V1_PNL_REPORTED   = 56_400.0
V1_DD_REPORTED    = 2_430.0   # likely the buggy reading; verify_v1_anchor.py confirms true $DD


# ---------------------------------------------------------------------------
# V1-COMPAT BASELINE PARAMS — V2 overrides that mimic V1 MGC behavior
# (Rob Reversal cannot be replicated; V1 MGC had it ON.)
# ---------------------------------------------------------------------------
V1_COMPAT_PARAMS = {
    # --- Core selectivity (V1 MGC values) ---
    "long_prep_threshold":  3,
    "long_threshold":       5,
    "short_prep_threshold": 3,
    "short_threshold":      5,
    "min_gap":              8,

    # --- Candle filter (V1 MGC) ---
    "max_candle_pct": 0.4,

    # --- Risk Management (V1 MGC) ---
    "sl_lookback":   15,
    "sl_max_points": 50.0,
    "rr_tp":         3.0,
    "tick_buffer":   2,
    "be_at_rr":      0.0,    # off — V1 had no BE

    # --- 1) Oscillator (V1 MGC) ---
    "osc_on":                 True,
    "hyper_wave_length":      5,
    "signal_type":            "SMA",
    "signal_length":          3,
    "mf_length":              35,
    "mf_smooth":              6,
    "hw_filter_on":           True,
    "hw_level":               16.0,
    "hw_extreme_filter_on":   False,    # V1 MGC: OFF
    "hw_extreme":             15.0,
    "sig_extreme_filter_on":  True,     # V1 MGC: ON
    "sig_extreme":            15.0,     # V1 shared hw_extreme value
    "cloud_filter_on":        True,
    "delta_filter_on":        True,
    "cloud_zero_filter_on":   False,    # V1 didn't have this
    "delta_off_mode":         "both",   # V1 behavior
    "pts_hw_sens":            1,
    "pts_hw_value":           1,
    "pts_hw_extreme":         1,
    "pts_sig_extreme":        1,
    "pts_cloud":              1,
    "pts_delta":              1,
    "pts_cloud_zero":         0,        # neutralised

    # --- 2) Double EMA (V1 MGC) ---
    "ema_on":         True,
    "ema_prin_len":   30,
    "ema_sec_len":    9,       # V1 MGC was 9 (vs MNQ's 20)
    "pts_ema_break":  1,
    "pts_ema_align":  1,

    # --- 3) Supertrend (V1 MGC) ---
    "st_on":   True,
    "st_atr":  10,             # V1 MGC was 10 (vs MNQ's 14)
    "st_mult": 3.0,
    "pts_st":  1,

    # --- 4) Alligator (V1 MGC) ---
    "alligator_on":    True,
    "jaw_length":      13,
    "teeth_length":    8,
    "lips_length":     5,
    "jaw_offset":      8,
    "teeth_offset":    5,
    "lips_offset":     3,
    "pts_alligator":   1,
    "pts_alli_offset": 1,
    "pts_retest_lips": 1,

    # --- 5) UT Bot (V1 MGC: OFF) ---
    "ut_on":         False,
    "ut_key":        1.0,
    "ut_atr_period": 10,
    "pts_ut_bot":    1,

    # --- 6) STC (V1 MGC) ---
    "stc_on":        True,
    "stc_length":    10,
    "stc_fast_len":  32,
    "stc_slow_len":  50,
    "stc_min_long":  1.0,
    "stc_max_long":  99.0,
    "stc_min_short": 1.0,
    "stc_max_short": 99.0,
    "pts_stc":       1,

    # --- 7) HMA Ribbon + SSL (V1 MGC + V2 V1-compat for SSL bucket) ---
    "hma_on":          True,
    "hma_ema_len":     7,
    "hma1_len":        42,
    "hma2_len":        84,
    "amp_mult":        2.0,    # V1 MGC was 2.0
    "hma_pol_bars":   -1,      # V1-compat: disable polarity tolerance
    "ssl_len":         60,
    "ssl_mult":        0.2,
    "hma_window_bars": 0,      # V1-compat: neutralise SSL cross
    "pts_hma_break":   1,
    "pts_hma_slow":    0,      # V1-compat: neutralise SSL cross bucket
}


# V1 MGC's actual blackout windows (active=true) — these are the anchor.
# - 12:30-14:00 (US lunch midday)
# - 17:00-21:00 (late US session)
# - 22:00-23:59 (CME close lock)
V1_MGC_WINDOWS = [(12, 30, 14, 0), (17, 0, 21, 0), (22, 0, 23, 59)]


def anchor_engine():
    """V1 MGC's blackout windows + auto_close at 22:00."""
    return build_engine(V1_MGC_WINDOWS)


def build_engine(active_windows):
    """Custom engine for blackout sweeps. `active_windows` is a list of
    (start_h, start_m, end_h, end_m); the 22-23:59 close lock is always
    enforced (auto-added if missing)."""
    from backend.api import BacktestEngineSettings, BlackoutWindowSettings

    blackouts = [
        BlackoutWindowSettings(
            active=True, start_hour=sh, start_minute=sm,
            end_hour=eh, end_minute=em
        )
        for sh, sm, eh, em in active_windows
    ]
    has_late = any(
        w.start_hour == 22 and w.end_hour == 23 and w.end_minute == 59
        for w in blackouts
    )
    if not has_late:
        blackouts.append(
            BlackoutWindowSettings(
                active=True, start_hour=22, start_minute=0,
                end_hour=23, end_minute=59
            )
        )
    return BacktestEngineSettings(
        auto_close_enabled=True,
        auto_close_hour=22,
        auto_close_minute=0,
        blackout_windows=blackouts,
        debug=False,
        daily_win_limit_enabled=False,
        daily_win_limit=500.0,
        daily_loss_limit_enabled=False,
        daily_loss_limit=700.0,
        daily_limit_mode="after_close",
    )
