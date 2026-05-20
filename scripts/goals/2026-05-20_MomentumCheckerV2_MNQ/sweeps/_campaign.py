"""Campaign constants for 2026-05-20 MomentumCheckerV2 MNQ 7m.

Starting point: V1 preset "New base - MomentumChecker - MNQ 7m" (PnL=$61,313,
DD=$2,143, N=785, WR=39.6%, PF=1.5) translated to V2 with V1-compat params.

Goal: maximise PnL; DD must stay ≤ V1 DD ($2,143) — strict; target DD < $2,000.

Fixed by user constraint:
  - symbol  = MNQ
  - tf      = 7m
  - period  = 2025-01-07 → 2026-05-15
  - max contracts = 20
  - no daily win/loss limits
  - auto_close = 22:00 (CME close, reference Brussels)
"""

from __future__ import annotations

STRATEGY = "MomentumCheckerV2"
SYMBOL = "MNQ"
INTERVAL = "7m"

# Same period as the V1 preset.
START = "2025-01-07T00:00"
END   = "2026-05-15T22:59"

INITIAL_EQUITY = 50_000.0
MAX_CONTRACTS = 20

# V1 preset risk; will be fine-tuned in phase 9.
RISK_PER_TRADE = 0.006  # 0.6%

# Strict DD cap (V1 anchor). Target: get under 2_000.
DD_CEILING = 2_143.0
DD_TARGET = 2_000.0

# Anchor metrics (from verify run on 2026-05-20):
ANCHOR_PNL = 61_313.06
ANCHOR_DD = 2_143.0
ANCHOR_TRADES = 785
ANCHOR_WR = 39.6
ANCHOR_PF = 1.5


# ---------------------------------------------------------------------------
# V1-compat anchor params: the V1 preset translated to V2 (same translation as
# scripts/verify_momentum_checker_v2_vs_v1.py). This is the "do nothing" point
# of the search — every sweep starts from here.
# ---------------------------------------------------------------------------
ANCHOR_PARAMS = {
    # --- Core selectivity ---
    "long_prep_threshold":  3,
    "long_threshold":       5,
    "short_prep_threshold": 3,
    "short_threshold":      5,
    "min_gap":              9,

    # --- Candle filter ---
    "max_candle_pct": 0.4,

    # --- Risk Management ---
    "sl_lookback":   5,
    "sl_max_points": 100.0,
    "rr_tp":         2.5,
    "tick_buffer":   0,
    "be_at_rr":      0.0,   # V2-new; 0 disables BE move (V1 behaviour)

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
    "sig_extreme_filter_on":  True,    # V1 had it OFF → V2 no-op (threshold 1e9)
    "sig_extreme":            1e9,
    "cloud_filter_on":        True,
    "delta_filter_on":        True,
    "cloud_zero_filter_on":   False,   # V2-new
    "delta_off_mode":         "both",  # V1 behaviour
    "pts_hw_sens":            1,
    "pts_hw_value":           1,
    "pts_hw_extreme":         1,
    "pts_sig_extreme":        1,
    "pts_cloud":              1,
    "pts_delta":              1,
    "pts_cloud_zero":         0,       # V2-new, neutralised

    # --- 2) Double EMA ---
    "ema_on":         True,
    "ema_prin_len":   30,
    "ema_sec_len":    20,
    "pts_ema_break":  1,
    "pts_ema_align":  1,

    # --- 3) Supertrend ---
    "st_on":   True,
    "st_atr":  14,
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

    # --- 7) HMA Ribbon + SSL (V2 adds SSL/slow-cross) ---
    "hma_on":          True,
    "hma_ema_len":     7,
    "hma1_len":        42,
    "hma2_len":        84,
    "amp_mult":        2.5,
    "hma_pol_bars":    -1,      # V1: disabled
    "ssl_len":         60,
    "ssl_mult":        0.2,
    "hma_window_bars": 0,       # irrelevant when pts_hma_slow=0
    "pts_hma_break":   1,
    "pts_hma_slow":    0,       # V1: V2 SSL-slow bucket neutralised
}


def anchor_engine():
    """Engine settings from the V1 preset (with blackouts active). This is the
    'do nothing' engine — every sweep starts from here so we measure pure
    strategy-param effect with the same gating as V1.

    Active windows: 09-10, 13-14, 17-23:59.
    """
    from backend.api import BacktestEngineSettings, BlackoutWindowSettings

    return BacktestEngineSettings(
        auto_close_enabled=True,
        auto_close_hour=22,
        auto_close_minute=0,
        blackout_windows=[
            BlackoutWindowSettings(active=True,  start_hour=9,  start_minute=0,  end_hour=10, end_minute=0),
            BlackoutWindowSettings(active=True,  start_hour=13, start_minute=0,  end_hour=14, end_minute=0),
            BlackoutWindowSettings(active=True,  start_hour=17, start_minute=0,  end_hour=23, end_minute=59),
            BlackoutWindowSettings(active=False, start_hour=15, start_minute=30, end_hour=15, end_minute=35),
            BlackoutWindowSettings(active=False, start_hour=16, start_minute=30, end_hour=22, end_minute=0),
            BlackoutWindowSettings(active=False, start_hour=21, start_minute=0,  end_hour=23, end_minute=59),
            BlackoutWindowSettings(active=False, start_hour=9,  start_minute=0,  end_hour=10, end_minute=0),
            BlackoutWindowSettings(active=False, start_hour=13, start_minute=0,  end_hour=14, end_minute=0),
            BlackoutWindowSettings(active=False, start_hour=17, start_minute=0,  end_hour=21, end_minute=0),
        ],
        debug=False,
        daily_win_limit_enabled=False,
        daily_win_limit=800.0,
        daily_loss_limit_enabled=False,
        daily_loss_limit=700.0,
        daily_limit_mode="after_close",
    )


def minimal_engine():
    """Only 22:00-23:59 active (CME daily close lock). Used in phase 8 if we
    want to re-explore blackouts from a clean state instead of patching the
    V1 windows."""
    from backend.api import BacktestEngineSettings, BlackoutWindowSettings

    return BacktestEngineSettings(
        auto_close_enabled=True,
        auto_close_hour=22,
        auto_close_minute=0,
        blackout_windows=[
            BlackoutWindowSettings(active=True, start_hour=22, start_minute=0, end_hour=23, end_minute=59),
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
    tuples (start_h, start_m, end_h, end_m) plus always the 22-23:59 lock."""
    from backend.api import BacktestEngineSettings, BlackoutWindowSettings

    blackouts = [
        BlackoutWindowSettings(
            active=True, start_hour=sh, start_minute=sm, end_hour=eh, end_minute=em
        )
        for sh, sm, eh, em in active_windows
    ]
    # Always lock the daily 22-23:59 window unless already in active_windows.
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
