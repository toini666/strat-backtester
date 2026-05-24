"""Campaign-local constants for 2026-05-24 MomentumCheckerV2 MGC v5 (PnL focus).

Seed: v4 WR WINNER (`BESTWR-MGC MomentumCheckerV2 - MGC 7m v4`) in `data/presets.json`.

Goal: **Maximise PnL** under WR >= 50 % and DD <= $2,500.
Budget: 500 sims.

Locks (per user):
- symbol = MGC, interval = 7m, max_contracts = 20
- initialEquity = $50,000
- Period: 2025-01-02 -> 2026-05-22 (full MGC 7m history)
- max_contracts, daily limits ticker (not directly addressed -> keep daily limits off)
- start/end dates locked

Free hand on:
- ALL strategy params
- Blackout windows (add / remove / shift)
- risk_per_trade

Math anchor (MCV2 has tp1_full_exit=True):
- Break-even WR = 1 / (1 + rr_tp)
- rr_tp=1.25 -> BE_WR=44.4 %, observed 51.0 %, edge ~6.6 pp
- rr_tp=1.30 -> BE_WR=43.5 %, edge ~6.6 pp -> ~50.1 % (at WR wall)
- rr_tp=1.35 -> BE_WR=42.6 %, edge ~6.6 pp -> ~49.2 % (BELOW)

WR margin (advisor): 95 % binomial CI ~+-3 pp on N=1056 -> SOFT WR floor ~51.5 %
to leave a safety buffer against noise/fresh-period drift.

The lowest-hanging fruit, per the v4 report's Pareto table:
    ALT_PNL (lb=14, risk=0.41 %, tb=1) -> PnL $28,817 / DD $2,536 / WR 50.9 % / N=1052
This is **$655 better** than the shipped v4 winner but $36 over DD budget. If we
can shave $36+ of DD via any lever (BO, threshold, filter), it dominates.
"""

from __future__ import annotations

# --- Locked engine identity ---
STRATEGY = "MomentumCheckerV2"
SYMBOL = "MGC"
INTERVAL = "7m"
START = "2025-01-02T00:00"
END = "2026-05-22T22:59"
INITIAL_EQUITY = 50_000.0
MAX_CONTRACTS = 20

# --- v4 WR WINNER seed ---------------------------------------------------
# Full param dict mirrored from data/presets.json (BESTWR-MGC v4)
SEED_PARAMS = {
    "long_prep_threshold": 3,
    "long_threshold": 5,
    "short_prep_threshold": 3,
    "short_threshold": 5,
    "min_gap": 8,
    "max_candle_pct": 0.25,
    "sl_lookback": 14,
    "sl_max_points": 120.0,
    "sl_min_pct": 0.0,
    "rr_tp": 1.25,
    "tick_buffer": 0,
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
    "sig_filter_on": False,
    "sig_level": 10.0,
    "sig_range_reject": False,
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
    "ut_key": 1.6,
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

# v4 winner: 0.42 % risk
SEED_RISK_PCT = 0.0042

# v4 winner: 7 active blackouts (5 seed + 07-08 + 12-12:30)
SEED_BLACKOUTS_ACTIVE = [
    (7, 0, 8, 0),
    (12, 0, 12, 30),
    (12, 30, 14, 0),
    (15, 30, 17, 0),
    (18, 0, 19, 0),
    (20, 0, 21, 0),
    (22, 0, 23, 59),
]
SEED_AUTO_CLOSE_H = 22
SEED_AUTO_CLOSE_M = 0


def build_engine_settings(blackouts=None, auto_close_h=22, auto_close_m=0,
                          daily_win_on=False, daily_loss_on=False,
                          daily_limit_mode="after_close"):
    """Build engine settings with arbitrary blackout list (tuples)."""
    from backend.api import BacktestEngineSettings, BlackoutWindowSettings
    if blackouts is None:
        blackouts = SEED_BLACKOUTS_ACTIVE
    bw = [
        BlackoutWindowSettings(
            active=True, start_hour=sh, start_minute=sm, end_hour=eh, end_minute=em
        )
        for (sh, sm, eh, em) in blackouts
    ]
    return BacktestEngineSettings(
        auto_close_enabled=True,
        auto_close_hour=auto_close_h,
        auto_close_minute=auto_close_m,
        blackout_windows=bw,
        debug=False,
        daily_win_limit_enabled=daily_win_on,
        daily_win_limit=500.0,
        daily_loss_limit_enabled=daily_loss_on,
        daily_loss_limit=700.0,
        daily_limit_mode=daily_limit_mode,
    )


def build_seed_engine_settings():
    return build_engine_settings(SEED_BLACKOUTS_ACTIVE,
                                 SEED_AUTO_CLOSE_H, SEED_AUTO_CLOSE_M)


def seed_kwargs(**overrides):
    """Return run_backtest kwargs initialised from the seed; merge overrides."""
    params = dict(SEED_PARAMS)
    if "params" in overrides:
        params.update(overrides.pop("params"))
    risk = overrides.pop("risk_per_trade", SEED_RISK_PCT)
    es = overrides.pop("engine_settings", build_seed_engine_settings())
    start = overrides.pop("start", START)
    end = overrides.pop("end", END)
    max_contracts = overrides.pop("max_contracts", MAX_CONTRACTS)
    return dict(
        strategy_name=STRATEGY,
        symbol=SYMBOL,
        interval=INTERVAL,
        start=start,
        end=end,
        initial_equity=INITIAL_EQUITY,
        risk_per_trade=risk,
        max_contracts=max_contracts,
        strategy_params=params,
        engine_settings=es,
        **overrides,
    )
