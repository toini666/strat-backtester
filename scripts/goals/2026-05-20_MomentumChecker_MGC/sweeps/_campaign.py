"""Campaign constants for 2026-05-20 MomentumChecker MGC 7m.

Goal: maximise PnL with max_drawdown_$ <= $2,500 (strict), at most 500 sims.

Starting from a clean configuration:
- Strategy params: MomentumChecker.default_params (no overrides)
- Engine: only one active blackout window, 22:00-23:59 (per user instruction)
- Risk: 0.5% per trade, max 20 contracts (per user instruction)
- No daily win/loss limits

MGC specs (from backend/api.py): tick_size=0.10, tick_value=$1.00, point_value=$10.
Available data: 2025-01-02 → 2026-05-15. Start at 2025-01-07 to give a buffer
before the first weekday trading session.
"""

from __future__ import annotations

STRATEGY = "MomentumChecker"
SYMBOL = "MGC"
INTERVAL = "7m"

# Full available history for MGC (allowing a couple of days for warmup buffer).
START = "2025-01-07T00:00"
END   = "2026-05-15T22:59"

INITIAL_EQUITY = 50_000.0
# User constraint: max 20 contracts (vs 50 on the MNQ campaign).
MAX_CONTRACTS = 20

# Same baseline risk as MNQ campaign — sweep will revisit this in Phase 7.
RISK_PER_TRADE = 0.005   # 0.5%

# Strict DD cap for any reported winner.
MAX_DD_BUDGET = 2_500.0

# Strategy baseline = MomentumChecker.default_params verbatim (no override).
# Pulling them in here so sweeps can build deltas without importing the strategy.
BASELINE_PARAMS = {
    # Configuration principale
    "long_prep_threshold":  3,
    "long_threshold":       5,
    "short_prep_threshold": 3,
    "short_threshold":      5,
    "min_gap":              4,
    # Filtre bougie
    "max_candle_pct": 0.4,
    # Risk Management
    "sl_lookback":   5,
    "sl_max_points": 100.0,
    "rr_tp":         2.0,
    "tick_buffer":   2,
    # 1) Oscillateur
    "osc_on":              True,
    "hyper_wave_length":   5,
    "signal_type":         "SMA",
    "signal_length":       3,
    "mf_length":           35,
    "mf_smooth":           6,
    "hw_filter_on":        True,
    "hw_level":            16.0,
    "hw_extreme_filter_on":  False,
    "sig_extreme_filter_on": False,
    "hw_extreme":          20.0,
    "pts_hw_sens":         1,
    "pts_hw_value":        1,
    "pts_hw_extreme":      1,
    "pts_sig_extreme":     1,
    "pts_cloud":           1,
    "pts_delta":           1,
    # 2) Double EMA
    "ema_on":          True,
    "ema_prin_len":    30,
    "ema_sec_len":     9,
    "pts_ema_break":   1,
    "pts_ema_align":   1,
    # 3) Supertrend
    "st_on":     True,
    "st_atr":    10,
    "st_mult":   3.0,
    "pts_st":    1,
    # 4) Alligator
    "alligator_on":     True,
    "jaw_length":       13,
    "teeth_length":     8,
    "lips_length":      5,
    "jaw_offset":       8,
    "teeth_offset":     5,
    "lips_offset":      3,
    "pts_alligator":    1,
    "pts_alli_offset":  1,
    "pts_retest_lips":  1,
    # 5) UT Bot
    "ut_on":             True,
    "ut_key":            1.0,
    "ut_atr_period":     10,
    "use_heikin_ashi":   False,
    "pts_ut_bot":        1,
    # 6) Rob Reversal
    "rob_on":  True,
    "pts_rob": 1,
    # 7) STC
    "stc_on":         True,
    "stc_length":     12,
    "stc_fast_len":   26,
    "stc_slow_len":   50,
    "stc_min_long":   1.0,
    "stc_max_long":   99.0,
    "stc_min_short":  1.0,
    "stc_max_short":  99.0,
    "pts_stc":        1,
    # 8) HMA Ribbon
    "hma_on":         True,
    "hma_ema_len":    7,
    "hma1_len":       42,
    "hma2_len":       84,
    "amp_mult":       2.0,
    "pts_hma_break":  1,
}


def baseline_engine():
    """Engine settings for the MGC campaign.

    Only one active window: 22:00-23:59 (CME daily close lock).
    Auto-close at 22:00 (CME close in reference Brussels time).
    No daily win/loss limits.
    """
    from backend.api import BacktestEngineSettings, BlackoutWindowSettings

    return BacktestEngineSettings(
        auto_close_enabled=True,
        auto_close_hour=22,
        auto_close_minute=0,
        blackout_windows=[
            BlackoutWindowSettings(active=False, start_hour=0,  start_minute=0,  end_hour=0,  end_minute=5),
            BlackoutWindowSettings(active=False, start_hour=9,  start_minute=0,  end_hour=9,  end_minute=5),
            BlackoutWindowSettings(active=False, start_hour=12, start_minute=0,  end_hour=14, end_minute=0),
            BlackoutWindowSettings(active=False, start_hour=15, start_minute=30, end_hour=15, end_minute=35),
            BlackoutWindowSettings(active=False, start_hour=16, start_minute=30, end_hour=22, end_minute=0),
            BlackoutWindowSettings(active=True,  start_hour=22, start_minute=0,  end_hour=23, end_minute=59),
        ],
        debug=False,
        daily_win_limit_enabled=False,
        daily_win_limit=500.0,
        daily_loss_limit_enabled=False,
        daily_loss_limit=700.0,
        daily_limit_mode="after_close",
    )
