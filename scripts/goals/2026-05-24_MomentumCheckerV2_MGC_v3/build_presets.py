"""Build 3 presets for v3 campaign — WINNER + ALT_HIGHPNL + ALT_WR.

Run:
    python scripts/goals/2026-05-24_MomentumCheckerV2_MGC_v3/build_presets.py

Each is written as:
- `<name>_preset.json` locally
- inserted into `data/presets.json` (UI favorites)
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CAMPAIGN = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(CAMPAIGN))

from scripts.goals._shared.preset import build_preset, write_preset
from scripts.goals._shared.harness import run_backtest, summarize, fmt_summary
from sweeps._campaign import (  # type: ignore
    END,
    INITIAL_EQUITY,
    INTERVAL,
    MAX_CONTRACTS,
    SEED_AUTO_CLOSE_H,
    SEED_AUTO_CLOSE_M,
    SEED_BLACKOUTS_ACTIVE,
    SEED_PARAMS,
    START,
    STRATEGY,
    SYMBOL,
)
from backend.api import BacktestEngineSettings, BlackoutWindowSettings


def build_engine_settings():
    """Re-create the BEST2 engine: same 5 blackouts + AC 22:00."""
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


# ============================================================================
# 3 PRESETS — each is seed BEST2 + small param deltas
# ============================================================================

PRESETS = [
    {
        "name": "BEST3 MGC MomentumCheckerV2 v3 WINNER - MGC 7m",
        "filename": "winner_preset.json",
        "overrides": {
            "ut_on": True,
            "ut_key": 1.6,
            "ut_atr_period": 10,
            "sl_max_points": 120.0,
        },
        "risk": 0.0053,
    },
    {
        "name": "BEST3 MGC MomentumCheckerV2 v3 ALT_HIGHPNL - MGC 7m",
        "filename": "alt_highpnl_preset.json",
        "overrides": {
            "ut_on": True,
            "ut_key": 1.5,
            "ut_atr_period": 10,
            "ema_prin_len": 18,
            "ema_sec_len": 7,
            "sl_max_points": 120.0,
        },
        "risk": 0.0053,
    },
    {
        "name": "BEST3 MGC MomentumCheckerV2 v3 ALT_WR - MGC 7m",
        "filename": "alt_wr_preset.json",
        "overrides": {
            "ut_on": True,
            "ut_key": 1.5,
            "ut_atr_period": 10,
            "ema_prin_len": 15,
            "ema_sec_len": 7,
            "sl_max_points": 120.0,
        },
        "risk": 0.0053,
    },
]


def main() -> None:
    es = build_engine_settings()
    for spec in PRESETS:
        params = dict(SEED_PARAMS)
        params.update(spec["overrides"])

        r = run_backtest(
            strategy_name=STRATEGY,
            symbol=SYMBOL,
            interval=INTERVAL,
            start=START,
            end=END,
            strategy_params=params,
            initial_equity=INITIAL_EQUITY,
            risk_per_trade=spec["risk"],
            max_contracts=MAX_CONTRACTS,
            engine_settings=es,
        )
        s = summarize(r)
        print(f"\n=== {spec['name']} ===")
        print("Replay: " + fmt_summary(s))

        preset = build_preset(
            strategy_name=STRATEGY,
            symbol=SYMBOL,
            interval=INTERVAL,
            start=START,
            end=END,
            initial_equity=INITIAL_EQUITY,
            risk_per_trade_decimal=spec["risk"],
            max_contracts=MAX_CONTRACTS,
            strategy_param_overrides=params,
            engine_settings=es,
            metrics_summary=s,
            name=spec["name"],
        )
        out = CAMPAIGN / spec["filename"]
        write_preset(preset, out, insert_into_presets_json=True)
        print(f"Wrote: {out.name}  |  inserted into data/presets.json")


if __name__ == "__main__":
    main()
