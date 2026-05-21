"""Campaign constants for 2026-05-21 MomentumCheckerV2 MGC 7m — v2.

Seed: BEST-MGC MomentumCheckerV2 — MGC 7m — WINNER
  PnL=$58,249 / $DD=$2,486 / N=851 / WR=39.7% / PF=1.54 / risk=0.55%

Goal: keep PnL as high as possible AND drop $DD < $2,500
  (hard cap, satisfied by seed); stretch target: $DD < $2,000.

Prior MGC campaign (2026-05-20) concluded $DD < $2,000 is "structurally
infeasible" due to a 1-contract floor. However, the MNQ v3 campaign
discovered the `int(contracts)` cliff CAN BE SHIFTED via `sl_max_points`,
so this campaign primarily explores that lever + direction restriction
(explicit untested item from prior REPORT).

Fixed by user constraint:
  - symbol  = MGC
  - tf      = 7m
  - period  = 2025-01-07 → 2026-05-15
  - max contracts = 20
  - no daily win/loss limits
  - auto_close = 22:00 reference Brussels (CME close)
"""

from __future__ import annotations

STRATEGY = "MomentumCheckerV2"
SYMBOL = "MGC"
INTERVAL = "7m"

START = "2025-01-07T00:00"
END   = "2026-05-15T22:59"

INITIAL_EQUITY = 50_000.0
MAX_CONTRACTS = 20

# Seed preset risk
RISK_PER_TRADE = 0.0055

# Strict $DD constraints
DD_HARD_CAP    = 2_500.0   # user's hard target (seed satisfies it)
DD_SOFT_TARGET = 2_000.0   # stretch target

# Seed/anchor metrics (must reproduce within $50)
SEED_PNL = 58_249.0
SEED_DD  = 2_486.0
SEED_TRADES = 851
SEED_WR = 39.7


# ---------------------------------------------------------------------------
# SEED PRESET PARAMS — exact replica of BEST-MGC v2 winner preset
# ---------------------------------------------------------------------------
BASELINE_PARAMS = {
    # --- Core selectivity ---
    "long_prep_threshold":  3,    # informational only
    "long_threshold":       5,
    "short_prep_threshold": 3,    # informational only
    "short_threshold":      5,
    "min_gap":              8,

    # --- Candle filter ---
    "max_candle_pct": 0.3,

    # --- Risk Management ---
    "sl_lookback":   15,
    "sl_max_points": 100.0,
    "rr_tp":         3.0,
    "tick_buffer":   2,
    "be_at_rr":      2.0,

    # --- 1) Oscillator ---
    "osc_on":                 True,
    "hyper_wave_length":      5,
    "signal_type":            "SMA",
    "signal_length":          3,
    "mf_length":              35,
    "mf_smooth":              6,
    "hw_filter_on":           True,
    "hw_level":               16.0,
    "hw_extreme_filter_on":   False,
    "hw_extreme":             15.0,
    "sig_extreme_filter_on":  True,
    "sig_extreme":            15.0,
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
    "ema_sec_len":    5,
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
    "ut_on":         False,
    "ut_key":        1.0,
    "ut_atr_period": 10,
    "pts_ut_bot":    1,

    # --- 6) STC ---
    "stc_on":        True,
    "stc_length":    10,
    "stc_fast_len":  32,
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
    "amp_mult":        2.0,
    "hma_pol_bars":    -1,
    "ssl_len":         60,
    "ssl_mult":        0.2,
    "hma_window_bars": 5,
    "pts_hma_break":   1,
    "pts_hma_slow":    1,
}


def seed_engine():
    """Engine settings replicating the seed preset blackouts EXACTLY:
    active=True: 12:30-14:00, 18-19, 20-21, 22-23:59 (surgical, from v1 winner).
    """
    from backend.api import BacktestEngineSettings, BlackoutWindowSettings

    return BacktestEngineSettings(
        auto_close_enabled=True,
        auto_close_hour=22,
        auto_close_minute=0,
        blackout_windows=[
            BlackoutWindowSettings(active=True, start_hour=12, start_minute=30,
                                   end_hour=14, end_minute=0),
            BlackoutWindowSettings(active=True, start_hour=18, start_minute=0,
                                   end_hour=19, end_minute=0),
            BlackoutWindowSettings(active=True, start_hour=20, start_minute=0,
                                   end_hour=21, end_minute=0),
            BlackoutWindowSettings(active=True, start_hour=22, start_minute=0,
                                   end_hour=23, end_minute=59),
        ],
        debug=False,
        daily_win_limit_enabled=False,
        daily_win_limit=500.0,
        daily_loss_limit_enabled=False,
        daily_loss_limit=700.0,
        daily_limit_mode="after_close",
    )


def minimal_engine():
    """Engine option A: only the mandatory 22-23:59 close lock (strip
    all session blackouts so we have a clean slate for surgical placement).
    """
    from backend.api import BacktestEngineSettings, BlackoutWindowSettings

    return BacktestEngineSettings(
        auto_close_enabled=True,
        auto_close_hour=22,
        auto_close_minute=0,
        blackout_windows=[
            BlackoutWindowSettings(active=True, start_hour=22, start_minute=0,
                                   end_hour=23, end_minute=59),
        ],
        debug=False,
        daily_win_limit_enabled=False,
        daily_win_limit=500.0,
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
        daily_win_limit=500.0,
        daily_loss_limit_enabled=False,
        daily_loss_limit=700.0,
        daily_limit_mode="after_close",
    )
