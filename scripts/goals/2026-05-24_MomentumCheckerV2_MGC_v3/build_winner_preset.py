"""Build the winner preset for the v3 campaign.

Fills in the param overrides + engine settings + metrics, then writes
both `winner_preset.json` (standalone) and inserts into `data/presets.json`.

This script will be filled with the actual winning config once Phase 8/9 narrow it down.
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
    SEED_PARAMS,
    START,
    STRATEGY,
    SYMBOL,
)
from backend.api import BacktestEngineSettings, BlackoutWindowSettings


# ============================================================================
# WINNER CONFIG — placeholder, will be filled after Phase 8/9
# ============================================================================
WINNER_OVERRIDES = {
    # filled by the campaign
}

WINNER_RISK_PCT_DECIMAL = 0.0053  # 0.53% — placeholder

WINNER_BLACKOUTS = [
    (12, 30, 14, 0),
    (15, 30, 17, 0),
    (18, 0,  19, 0),
    (20, 0,  21, 0),
    (22, 0,  23, 59),
]

WINNER_NAME = "BEST3 MGC MomentumCheckerV2 - MGC 7m"


def build_engine_settings():
    bw = [
        BlackoutWindowSettings(
            active=True, start_hour=sh, start_minute=sm, end_hour=eh, end_minute=em
        )
        for (sh, sm, eh, em) in WINNER_BLACKOUTS
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


def main() -> None:
    params = dict(SEED_PARAMS)
    params.update(WINNER_OVERRIDES)
    es = build_engine_settings()

    r = run_backtest(
        strategy_name=STRATEGY,
        symbol=SYMBOL,
        interval=INTERVAL,
        start=START,
        end=END,
        strategy_params=params,
        initial_equity=INITIAL_EQUITY,
        risk_per_trade=WINNER_RISK_PCT_DECIMAL,
        max_contracts=MAX_CONTRACTS,
        engine_settings=es,
    )
    s = summarize(r)
    print("WINNER replay: " + fmt_summary(s))

    preset = build_preset(
        strategy_name=STRATEGY,
        symbol=SYMBOL,
        interval=INTERVAL,
        start=START,
        end=END,
        initial_equity=INITIAL_EQUITY,
        risk_per_trade_decimal=WINNER_RISK_PCT_DECIMAL,
        max_contracts=MAX_CONTRACTS,
        strategy_param_overrides=params,
        engine_settings=es,
        metrics_summary=s,
        name=WINNER_NAME,
    )
    out = CAMPAIGN / "winner_preset.json"
    write_preset(preset, out, insert_into_presets_json=True)
    print(f"\nWrote: {out}")
    print(f"Inserted into data/presets.json as: {WINNER_NAME}")


if __name__ == "__main__":
    main()
