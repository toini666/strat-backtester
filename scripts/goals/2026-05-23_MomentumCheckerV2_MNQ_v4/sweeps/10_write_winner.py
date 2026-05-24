"""Phase 10 — Build and write the WINNER preset.

WINNER config:
  ema_prin_len=34, ema_sec_len=18, st_atr=14, tick_buffer=0, sl_max_points=42,
  + BO+07:00-08:00 active
  + risk=0.625%

Expected: PnL $88,430 / DD $2,341 / WR 41.8% / N=765 / PF 1.72
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from scripts.goals._shared.harness import run_backtest, summarize, fmt_summary
from scripts.goals._shared.preset import build_preset, write_preset
from sweeps._campaign import (
    END, INITIAL_EQUITY, INTERVAL, MAX_CONTRACTS,
    SEED_PARAMS, SEED_BLACKOUTS, START, STRATEGY, SYMBOL,
    make_engine_settings,
)


WINNER_OVERRIDES = {
    "ema_prin_len": 34,
    "ema_sec_len": 18,
    "st_atr": 14,
    "tick_buffer": 0,
    "sl_max_points": 42,
}

WINNER_RISK = 0.00625  # 0.625%

# Add the +07:00-08:00 blackout to the seed blackouts.
WINNER_BLACKOUTS = SEED_BLACKOUTS + [
    {"active": True, "start_hour": 7, "start_minute": 0,
     "end_hour": 8, "end_minute": 0},
]


def main():
    # 1. Run the winner to capture metrics
    params = dict(SEED_PARAMS); params.update(WINNER_OVERRIDES)
    engine = make_engine_settings(blackouts=WINNER_BLACKOUTS)
    r = run_backtest(
        strategy_name=STRATEGY, symbol=SYMBOL, interval=INTERVAL,
        start=START, end=END, strategy_params=params,
        initial_equity=INITIAL_EQUITY, risk_per_trade=WINNER_RISK,
        max_contracts=MAX_CONTRACTS, engine_settings=engine,
    )
    s = summarize(r); s["label"] = "WINNER"
    print(f"{'WINNER':<60s} {fmt_summary(s)}")

    # 2. Build the preset
    preset = build_preset(
        strategy_name=STRATEGY,
        symbol=SYMBOL, interval=INTERVAL,
        start=START, end=END,
        initial_equity=INITIAL_EQUITY,
        risk_per_trade_decimal=WINNER_RISK,
        max_contracts=MAX_CONTRACTS,
        strategy_param_overrides=params,
        engine_settings=engine,
        metrics_summary=s,
        name="BEST-MNQ MomentumCheckerV2 - MNQ 7m v4",
    )

    # 3. Write standalone + insert into data/presets.json
    target = Path(__file__).resolve().parents[1] / "winner_preset.json"
    write_preset(preset, target)
    print(f"\nWinner preset written to: {target}")
    print("Also inserted in data/presets.json at top of favorites.")


if __name__ == "__main__":
    main()
