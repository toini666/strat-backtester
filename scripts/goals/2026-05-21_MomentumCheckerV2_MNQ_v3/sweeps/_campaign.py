"""Campaign constants for 2026-05-21 MomentumCheckerV2 MNQ 7m — v3.

Seed: user-provided v2 WINNER preset
  PnL=$80,565 / $DD=$3,023 / N=797 / WR=40.4% / PF=1.58 / risk=0.66%

Goal: keep PnL ≥ $80,565 (ideally beat it) AND drop $DD < $2,500.

User hints — areas left under-explored by v2:
  - threshold/min_gap COMBOS (only 1-D was tested in v2)
  - HMA canal params, inspired by HMASSLOsciV3 MNQ 7m winner
    (hma1=13, hma2=21, amp=2.0, pol_bars=0, ssl_len=80)
  - point weights combos (only single bumps to 2 in v2)

Advisor-driven refinements:
  - DD is the binding constraint → risk-geometry FIRST (be_at_rr promoted)
  - SEED preset blackouts used as anchor (13-14:30 extension is in seed,
    NOT in v2 _campaign.anchor_engine)
  - Re-validate baseline reproduces $80,565 / $3,023 within $50

Fixed by user constraint:
  - symbol  = MNQ
  - tf      = 7m
  - period  = 2025-01-07 → 2026-05-15
  - max contracts = 20
  - no daily win/loss limits
  - auto_close = 22:00 reference Brussels (CME close)
"""

from __future__ import annotations

STRATEGY = "MomentumCheckerV2"
SYMBOL = "MNQ"
INTERVAL = "7m"

START = "2025-01-07T00:00"
END   = "2026-05-15T22:59"

INITIAL_EQUITY = 50_000.0
MAX_CONTRACTS = 20

# Seed preset risk (v2 winner)
RISK_PER_TRADE = 0.0066

# Strict $DD constraints
DD_HARD_CAP   = 2_500.0   # user's hard target
DD_SOFT_TARGET = 2_000.0  # stretch target

# Seed/anchor metrics (must reproduce within $50)
SEED_PNL = 80_565.0
SEED_DD  = 3_023.0
SEED_TRADES = 797
SEED_WR = 40.4


# ---------------------------------------------------------------------------
# SEED PRESET PARAMS — exact replica of v2 WINNER preset received from user
# ---------------------------------------------------------------------------
BASELINE_PARAMS = {
    # --- Core selectivity ---
    "long_prep_threshold":  3,    # informational only
    "long_threshold":       5,
    "short_prep_threshold": 3,    # informational only
    "short_threshold":      5,
    "min_gap":              9,

    # --- Candle filter ---
    "max_candle_pct": 0.3,

    # --- Risk Management ---
    "sl_lookback":   5,
    "sl_max_points": 60.0,
    "rr_tp":         2.5,
    "tick_buffer":   2,
    "be_at_rr":      0.0,

    # --- 1) Oscillator ---
    "osc_on":                 True,
    "hyper_wave_length":      5,
    "signal_type":            "SMA",
    "signal_length":          3,
    "mf_length":              35,
    "mf_smooth":              5,
    "hw_filter_on":           True,
    "hw_level":               16.0,
    "hw_extreme_filter_on":   True,
    "hw_extreme":             20.0,
    "sig_extreme_filter_on":  True,
    "sig_extreme":            40.0,
    "cloud_filter_on":        True,
    "delta_filter_on":        True,
    "cloud_zero_filter_on":   False,
    "delta_off_mode":         "both",
    "pts_hw_sens":            1,
    "pts_hw_value":           1,
    "pts_hw_extreme":         1,
    "pts_sig_extreme":        1,
    "pts_cloud":              1,
    "pts_delta":              1,
    "pts_cloud_zero":         0,

    # --- 2) Double EMA ---
    "ema_on":         True,
    "ema_prin_len":   30,
    "ema_sec_len":    20,
    "pts_ema_break":  1,
    "pts_ema_align":  1,

    # --- 3) Supertrend ---
    "st_on":   True,
    "st_atr":  10,
    "st_mult": 3.0,
    "pts_st":  1,

    # --- 4) Alligator ---
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

    # --- 5) UT Bot ---
    "ut_on":         True,
    "ut_key":        1.0,
    "ut_atr_period": 10,
    "pts_ut_bot":    1,

    # --- 6) STC ---
    "stc_on":        True,
    "stc_length":    12,
    "stc_fast_len":  26,
    "stc_slow_len":  50,
    "stc_min_long":  1.0,
    "stc_max_long":  99.0,
    "stc_min_short": 1.0,
    "stc_max_short": 99.0,
    "pts_stc":       1,

    # --- 7) HMA Ribbon + SSL ---
    "hma_on":          True,
    "hma_ema_len":     7,
    "hma1_len":        42,
    "hma2_len":        84,
    "amp_mult":        3.5,
    "hma_pol_bars":    -1,
    "ssl_len":         60,
    "ssl_mult":        0.2,
    "hma_window_bars": 5,
    "pts_hma_break":   1,
    "pts_hma_slow":    1,
}


def seed_engine():
    """Engine settings replicating the v2 WINNER preset EXACTLY:
    blackouts (active=True): 9-10, 13-14:30, 17-23:59, 22-23:59 (overlap
    with 17-24 is intentional — kept verbatim from seed for reproducibility).
    """
    from backend.api import BacktestEngineSettings, BlackoutWindowSettings

    return BacktestEngineSettings(
        auto_close_enabled=True,
        auto_close_hour=22,
        auto_close_minute=0,
        blackout_windows=[
            BlackoutWindowSettings(active=True, start_hour=9,  start_minute=0,
                                   end_hour=10, end_minute=0),
            BlackoutWindowSettings(active=True, start_hour=13, start_minute=0,
                                   end_hour=14, end_minute=30),
            BlackoutWindowSettings(active=True, start_hour=17, start_minute=0,
                                   end_hour=23, end_minute=59),
            BlackoutWindowSettings(active=True, start_hour=22, start_minute=0,
                                   end_hour=23, end_minute=59),
        ],
        debug=False,
        daily_win_limit_enabled=False,
        daily_win_limit=800.0,
        daily_loss_limit_enabled=False,
        daily_loss_limit=700.0,
        daily_limit_mode="after_close",
    )


def build_engine(active_windows):
    """Custom engine for blackout sweeps. `active_windows` is a list of
    tuples (start_h, start_m, end_h, end_m). The 22-23:59 close lock is
    always added if not already present."""
    from backend.api import BacktestEngineSettings, BlackoutWindowSettings

    blackouts = [
        BlackoutWindowSettings(
            active=True, start_hour=sh, start_minute=sm, end_hour=eh, end_minute=em
        )
        for sh, sm, eh, em in active_windows
    ]
    has_late = any(w.start_hour == 22 and w.end_hour == 23 for w in blackouts)
    if not has_late:
        blackouts.append(
            BlackoutWindowSettings(active=True, start_hour=22, start_minute=0,
                                   end_hour=23, end_minute=59)
        )
    return BacktestEngineSettings(
        auto_close_enabled=True,
        auto_close_hour=22,
        auto_close_minute=0,
        blackout_windows=blackouts,
        debug=False,
        daily_win_limit_enabled=False,
        daily_win_limit=800.0,
        daily_loss_limit_enabled=False,
        daily_loss_limit=700.0,
        daily_limit_mode="after_close",
    )
