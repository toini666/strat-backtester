"""Campaign-local constants for the 2026-05-23 MCV2 MNQ v4 campaign.

Goal: improve PnL ≥ seed, keep $-DD ≤ seed (recomputed from baseline),
increase win rate via new params `sl_min_pct` and `sig_filter_on` family.

Frozen by user:
    SYMBOL = "MNQ", INTERVAL = "7m"
    START = "2025-01-07T00:00", END = "2026-05-15T22:59"
    MAX_CONTRACTS = 20
    Daily limits OFF.
"""
from __future__ import annotations

STRATEGY = "MomentumCheckerV2"
SYMBOL = "MNQ"
INTERVAL = "7m"
START = "2025-01-07T00:00"
END = "2026-05-15T22:59"
INITIAL_EQUITY = 50_000.0
MAX_CONTRACTS = 20

# Seed (BEST-MNQ MomentumCheckerV2 - MNQ 7m, presets.json id a423fc68-…).
# riskPerTrade in preset is in percent (0.6 means 0.6 %); harness expects fraction.
SEED_RISK = 0.006  # 0.6 % → fraction

SEED_PARAMS = {
    "long_prep_threshold": 3,
    "long_threshold": 5,
    "short_prep_threshold": 3,
    "short_threshold": 5,
    "min_gap": 10,
    "max_candle_pct": 0.3,
    "sl_lookback": 5,
    "sl_max_points": 41,
    "rr_tp": 2.5,
    "tick_buffer": 2,
    "be_at_rr": 0,
    "osc_on": True,
    "hyper_wave_length": 5,
    "signal_type": "SMA",
    "signal_length": 3,
    "mf_length": 35,
    "mf_smooth": 5,
    "hw_filter_on": True,
    "hw_level": 16,
    "hw_extreme_filter_on": True,
    "hw_extreme": 20,
    "sig_extreme_filter_on": True,
    "sig_extreme": 40,
    "cloud_filter_on": True,
    "delta_filter_on": True,
    "cloud_zero_filter_on": False,
    "delta_off_mode": "both",
    "pts_hw_sens": 1,
    "pts_hw_value": 1,
    "pts_hw_extreme": 1,
    "pts_sig_extreme": 1,
    "pts_cloud": 1,
    "pts_delta": 1,
    "pts_cloud_zero": 0,
    "ema_on": True,
    "ema_prin_len": 30,
    "ema_sec_len": 20,
    "pts_ema_break": 1,
    "pts_ema_align": 2,
    "st_on": True,
    "st_atr": 10,
    "st_mult": 3,
    "pts_st": 1,
    "alligator_on": True,
    "jaw_length": 13,
    "teeth_length": 8,
    "lips_length": 5,
    "jaw_offset": 8,
    "teeth_offset": 5,
    "lips_offset": 3,
    "pts_alligator": 1,
    "pts_alli_offset": 1,
    "pts_retest_lips": 1,
    "ut_on": True,
    "ut_key": 1,
    "ut_atr_period": 10,
    "pts_ut_bot": 1,
    "stc_on": True,
    "stc_length": 12,
    "stc_fast_len": 26,
    "stc_slow_len": 50,
    "stc_min_long": 1,
    "stc_max_long": 99,
    "stc_min_short": 1,
    "stc_max_short": 99,
    "pts_stc": 1,
    "hma_on": True,
    "hma_ema_len": 7,
    "hma1_len": 42,
    "hma2_len": 84,
    "amp_mult": 3.5,
    "hma_pol_bars": 0,
    "ssl_len": 60,
    "ssl_mult": 0.2,
    "hma_window_bars": 5,
    "pts_hma_break": 1,
    "pts_hma_slow": 1,
    # New params introduced since the v3 campaign.
    "sl_min_pct": 0.0,
    "sig_filter_on": False,
    "sig_level": 10.0,
    "sig_range_reject": False,
    "pts_sig_value": 1,
}

# Engine settings — taken verbatim from preset (auto_close=22, four blackouts).
SEED_BLACKOUTS = [
    {"active": True, "start_hour": 9,  "start_minute": 0,  "end_hour": 10, "end_minute": 0},
    {"active": True, "start_hour": 13, "start_minute": 0,  "end_hour": 14, "end_minute": 30},
    {"active": True, "start_hour": 17, "start_minute": 0,  "end_hour": 23, "end_minute": 59},
    {"active": True, "start_hour": 22, "start_minute": 0,  "end_hour": 23, "end_minute": 59},
]


def make_engine_settings(blackouts=None):
    """Return a BacktestEngineSettings with the seed's UI-aligned engine config.

    Falls back to SEED_BLACKOUTS when no override is given. Daily limits OFF.
    auto_close fixed at 22:00.
    """
    from backend.api import BacktestEngineSettings, BlackoutWindowSettings
    bos = blackouts if blackouts is not None else SEED_BLACKOUTS
    return BacktestEngineSettings(
        auto_close_enabled=True,
        auto_close_hour=22,
        auto_close_minute=0,
        blackout_windows=[BlackoutWindowSettings(**bo) for bo in bos],
        debug=False,
        daily_win_limit_enabled=False,
        daily_win_limit=800.0,
        daily_loss_limit_enabled=False,
        daily_loss_limit=700.0,
        daily_limit_mode="after_close",
    )
