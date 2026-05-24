"""Campaign-local constants for 2026-05-24 MomentumCheckerV2 MGC v3.

Seed: `BEST2 MGC MomentumCheckerV2 - MGC 7m` (preset in `data/presets.json`).

Goal: improve PnL, keep DD ≤ seed (measured in $), ideally raise WR.

User-specified locked fields:
- symbol = MGC, interval = 7m, max_contracts = 20
- initialEquity = $50,000
- start = 2025-01-07T00:00, end = 2026-05-15T22:59
- auto_close = 22:00 (already at the canonical CME close)
- daily limits OFF

Two NEW params introduced since BEST2:
- sl_min_pct  — minimum SL as % of entry price (0 disables)
- sig_range_reject — when True, drop entries with |sig| ≤ sig_level
"""

from __future__ import annotations

# --- Locked engine identity ---
STRATEGY = "MomentumCheckerV2"
SYMBOL = "MGC"
INTERVAL = "7m"
START = "2025-01-07T00:00"
END = "2026-05-15T22:59"
INITIAL_EQUITY = 50_000.0
MAX_CONTRACTS = 20

# --- Seed BEST2 -----------------------------------------------------------
# Full param dict (mirrors what's in data/presets.json under
# "BEST2 MGC MomentumCheckerV2 - MGC 7m").
SEED_PARAMS = {
    "long_prep_threshold": 3,
    "long_threshold": 5,
    "short_prep_threshold": 3,
    "short_threshold": 5,
    "min_gap": 8,
    "max_candle_pct": 0.25,
    "sl_lookback": 15,
    "sl_max_points": 100,
    "sl_min_pct": 0.0,          # NEW — preset uses default
    "rr_tp": 3,
    "tick_buffer": 2,
    "be_at_rr": 2,
    "osc_on": True,
    "hyper_wave_length": 5,
    "signal_type": "SMA",
    "signal_length": 3,
    "mf_length": 35,
    "mf_smooth": 6,
    "hw_filter_on": True,
    "hw_level": 16,
    "hw_extreme_filter_on": False,
    "hw_extreme": 15,
    "sig_filter_on": False,      # NEW bonus — preset uses default
    "sig_level": 10.0,           # NEW — preset uses default
    "sig_range_reject": False,   # NEW reject — preset uses default
    "sig_extreme_filter_on": True,
    "sig_extreme": 15,
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
    "ema_prin_len": 30,
    "ema_sec_len": 5,
    "pts_ema_break": 1,
    "pts_ema_align": 1,
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
    "ut_on": False,
    "ut_key": 1,
    "ut_atr_period": 10,
    "pts_ut_bot": 1,
    "stc_on": True,
    "stc_length": 10,
    "stc_fast_len": 32,
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
    "amp_mult": 2,
    "hma_pol_bars": 0,
    "ssl_len": 60,
    "ssl_mult": 0.2,
    "hma_window_bars": 5,
    "pts_hma_break": 1,
    "pts_hma_slow": 1,
}

SEED_RISK_PCT = 0.0053  # 0.53 %  — stored as decimal here

# --- BEST2 engine settings ------------------------------------------------
# 5 ACTIVE blackouts (different from the UI default block layout):
SEED_BLACKOUTS_ACTIVE = [
    (12, 30, 14, 0),
    (15, 30, 17, 0),
    (18, 0,  19, 0),
    (20, 0,  21, 0),
    (22, 0,  23, 59),
]
SEED_AUTO_CLOSE_H = 22
SEED_AUTO_CLOSE_M = 0


def build_seed_engine_settings():
    """Recreate the BEST2 engine settings exactly (5 active windows, AC 22:00)."""
    from backend.api import BacktestEngineSettings, BlackoutWindowSettings
    bw = [
        BlackoutWindowSettings(
            active=True, start_hour=sh, start_minute=sm, end_hour=eh, end_minute=em
        )
        for (sh, sm, eh, em) in SEED_BLACKOUTS_ACTIVE
    ]
    return BacktestEngineSettings(
        auto_close_enabled=True,
        auto_close_hour=SEED_AUTO_CLOSE_H,
        auto_close_minute=SEED_AUTO_CLOSE_M,
        blackout_windows=bw,
        debug=False,
        daily_win_limit_enabled=False,
        daily_win_limit=500.0,
        daily_loss_limit_enabled=False,
        daily_loss_limit=700.0,
        daily_limit_mode="after_close",
    )


def seed_kwargs(**overrides):
    """Return run_backtest kwargs initialised from the seed; merge overrides."""
    params = dict(SEED_PARAMS)
    if "params" in overrides:
        params.update(overrides.pop("params"))
    risk = overrides.pop("risk_per_trade", SEED_RISK_PCT)
    es = overrides.pop("engine_settings", build_seed_engine_settings())
    return dict(
        strategy_name=STRATEGY,
        symbol=SYMBOL,
        interval=INTERVAL,
        start=START,
        end=END,
        initial_equity=INITIAL_EQUITY,
        risk_per_trade=risk,
        max_contracts=MAX_CONTRACTS,
        strategy_params=params,
        engine_settings=es,
        **overrides,
    )
