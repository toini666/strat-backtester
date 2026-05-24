"""Campaign-local constants for MNQ MomentumCheckerV2 v5 WR-focused campaign.

Goal: WR ≥ 50 %, DD ≤ $2,500, maximise PnL — starting from BESTNEW-MNQ
MomentumCheckerV2 - MNQ 7m v4 (PnL $88,430 / DD $2,341 / WR 41.8 %).
"""

from __future__ import annotations

# Period — full available MNQ 7m history (data: 2025-01-02 → 2026-05-22)
START = "2025-01-07T00:00"   # v4 used this start
END   = "2026-05-22T23:00"   # extended a week vs v4 (was 2026-05-15)

SYMBOL   = "MNQ"
INTERVAL = "7m"
STRATEGY = "MomentumCheckerV2"

INITIAL_EQUITY = 50_000.0
MAX_CONTRACTS  = 20

# Seed = v4 winner (the user's starting preset)
SEED_RISK = 0.625 / 100  # 0.625 %

SEED_PARAMS = {
    "long_prep_threshold": 3,
    "long_threshold": 5,
    "short_prep_threshold": 3,
    "short_threshold": 5,
    "min_gap": 10,
    "max_candle_pct": 0.3,
    "sl_lookback": 5,
    "sl_max_points": 42,
    "sl_min_pct": 0.0,
    "rr_tp": 2.5,
    "tick_buffer": 0,
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
    "sig_filter_on": False,
    "sig_level": 10.0,
    "sig_range_reject": False,
    "sig_extreme_filter_on": True,
    "sig_extreme": 40,
    "cloud_filter_on": True,
    "delta_filter_on": True,
    "cloud_zero_filter_on": False,
    "delta_off_mode": "both",
    "pts_hw_sens": 1,
    "pts_hw_value": 1,
    "pts_hw_extreme": 1,
    "pts_sig_value": 1,
    "pts_sig_extreme": 1,
    "pts_cloud": 1,
    "pts_delta": 1,
    "pts_cloud_zero": 0,
    "ema_on": True,
    "ema_prin_len": 34,
    "ema_sec_len": 18,
    "pts_ema_break": 1,
    "pts_ema_align": 2,
    "st_on": True,
    "st_atr": 14,
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
}

# Seed v4 active blackouts (reference Brussels time)
SEED_BLACKOUTS = [
    (9,  0, 10, 0),
    (13, 0, 14, 30),
    (17, 0, 23, 59),
    (22, 0, 23, 59),
    (7,  0, 8,  0),
]
SEED_AUTO_CLOSE = (22, 0)

GOAL_WR = 50.0
GOAL_DD = 2500.0
