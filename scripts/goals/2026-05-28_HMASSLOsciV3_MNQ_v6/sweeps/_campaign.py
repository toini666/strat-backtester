"""Campaign constants for 2026-05-28 HMASSLOsciV3 MNQ 7m v6.

Seed preset: "MNQ-PROD - HMASSLOsciV3 - MNQ 7m" (data/presets.json)
Goal: improve PnL (or keep similar) AND reduce DD vs seed.
Focus: new v3.1 params — min_sl_points, entry_cross_mode, ema_exit_ext_on + ema_exit_len.

Locked:
  - symbol / interval / dates
  - max_contracts = 20
  - daily limits OFF

Free:
  - all strategy params
  - blackout windows
  - risk_per_trade
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT.parent) not in sys.path:
    sys.path.insert(0, str(ROOT.parent))


STRATEGY = "HMASSLOsciV3"
SYMBOL = "MNQ"
INTERVAL = "7m"
START = "2025-01-06T00:00"
END = "2026-05-22T00:00"
INITIAL_EQUITY = 50_000.0
MAX_CONTRACTS = 20

SEED_RISK = 0.005  # 0.5%

# Seed strategy params — verbatim from "MNQ-PROD" preset
SEED_PARAMS = {
    "ema_len": 11,
    "hma1_len": 13,
    "hma2_len": 21,
    "amp_mult": 2,
    "hma_pol_bars": 0,
    "entry_window_bars": 3,
    "ssl_len": 80,
    "ssl_mult": 0.2,
    "hyper_wave_length": 7,
    "signal_type": "SMA",
    "signal_length": 4,
    "mf_length": 37,
    "mf_smooth": 7,
    "hw_dir_on": False,
    "hw_extreme_on": True,
    "hw_extreme": 20,
    "sig_extreme_on": True,
    "sig_extreme": 40,
    "hw_range_on": False,
    "hw_range": 10,
    "cloud_on": True,
    "delta_on": True,
    "cloud_zero_on": False,
    "delta_ext_on": False,
    "tick_buffer": 0,
    "max_sl_points": 300,
    "min_sl_points": 0,
    "cooldown_bars": 3,
    "max_candle_pct": 0.9,
    "signal_candle_sl_on": False,
    "one_trade_per_entry_window": True,
    "hw_partial_pct": 0,
    "hw_partial_min_rr": 0,
    "block_loss_exit_before_partial": False,
    "final_exit_mode": "HMA rapide/SSL → HW",
    "final_exit_pct": 0.1,
    "entry_cross_mode": "Baseline",
    "ema_exit_ext_on": False,
    "ema_exit_len": 9,
}

# Active blackouts from seed preset (reference Brussels time)
SEED_BLACKOUTS_ACTIVE = [
    (22, 0, 23, 59),
    (11, 0, 13, 0),
    (14, 0, 15, 0),
    (5, 0, 9, 0),
]


def seed_engine_settings():
    """Build the seed engine settings: UI default + the 4 active blackouts."""
    from backend.api import BacktestEngineSettings, BlackoutWindowSettings

    # The seed preset has 10 blackout window definitions (most inactive).
    # We rebuild exactly that list so a verify_preset replays correctly.
    raw = [
        {"active": False, "start_hour": 0,  "start_minute": 0,  "end_hour": 0,  "end_minute": 5},
        {"active": False, "start_hour": 9,  "start_minute": 0,  "end_hour": 9,  "end_minute": 5},
        {"active": False, "start_hour": 12, "start_minute": 0,  "end_hour": 14, "end_minute": 0},
        {"active": False, "start_hour": 15, "start_minute": 30, "end_hour": 15, "end_minute": 35},
        {"active": False, "start_hour": 16, "start_minute": 30, "end_hour": 22, "end_minute": 0},
        {"active": True,  "start_hour": 22, "start_minute": 0,  "end_hour": 23, "end_minute": 59},
        {"active": True,  "start_hour": 11, "start_minute": 0,  "end_hour": 13, "end_minute": 0},
        {"active": True,  "start_hour": 14, "start_minute": 0,  "end_hour": 15, "end_minute": 0},
        {"active": True,  "start_hour": 5,  "start_minute": 0,  "end_hour": 9,  "end_minute": 0},
        {"active": False, "start_hour": 12, "start_minute": 0,  "end_hour": 13, "end_minute": 0},
    ]
    return BacktestEngineSettings(
        auto_close_enabled=True,
        auto_close_hour=22,
        auto_close_minute=0,
        blackout_windows=[BlackoutWindowSettings(**w) for w in raw],
        debug=False,
        daily_win_limit_enabled=False,
        daily_win_limit=500.0,
        daily_loss_limit_enabled=False,
        daily_loss_limit=700.0,
        daily_limit_mode="after_close",
    )


def make_engine_settings(active_windows):
    """Build engine settings with the given list of active (sh,sm,eh,em) windows.

    auto_close stays 22:00, daily limits off, all other windows inactive.
    """
    from backend.api import BacktestEngineSettings, BlackoutWindowSettings

    wins = [BlackoutWindowSettings(active=True, start_hour=sh, start_minute=sm,
                                   end_hour=eh, end_minute=em)
            for (sh, sm, eh, em) in active_windows]
    return BacktestEngineSettings(
        auto_close_enabled=True,
        auto_close_hour=22,
        auto_close_minute=0,
        blackout_windows=wins,
        debug=False,
        daily_win_limit_enabled=False,
        daily_win_limit=500.0,
        daily_loss_limit_enabled=False,
        daily_loss_limit=700.0,
        daily_limit_mode="after_close",
    )


def run_seed_kwargs(params=None, engine_settings=None, risk=None):
    return dict(
        strategy_name=STRATEGY,
        symbol=SYMBOL,
        interval=INTERVAL,
        start=START,
        end=END,
        initial_equity=INITIAL_EQUITY,
        risk_per_trade=risk if risk is not None else SEED_RISK,
        max_contracts=MAX_CONTRACTS,
        strategy_params=dict(SEED_PARAMS, **(params or {})),
        engine_settings=engine_settings if engine_settings is not None else seed_engine_settings(),
    )
