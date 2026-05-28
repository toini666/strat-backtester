"""Sweep 10 — build the WINNER preset and verify it.

WINNER = TOP_C @ risk=0.60%
  params overrides on seed:
    hma_pol_bars: 0 → 5
    sig_extreme:  40 → 60
    hw_extreme:   20 → 35
    mf_length:    37 → 31
  blackouts (active):
    22-23:59  (kept — close)
    6-9       (replaces seed 5-9)
    11-14     (replaces seed 11-13)
    14h30-15  (replaces seed 14-15)
  risk: 0.50% → 0.60%

Expected: PnL=$80,709 / DD=$3,236 / N=1299
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1]))

from _shared.harness import run_backtest, summarize, fmt_summary  # noqa: E402
from _shared.preset import build_preset, write_preset  # noqa: E402
from _campaign import (  # noqa: E402
    STRATEGY, SYMBOL, INTERVAL, START, END, INITIAL_EQUITY, MAX_CONTRACTS,
    SEED_PARAMS,
)
from backend.api import BacktestEngineSettings, BlackoutWindowSettings  # noqa: E402


WINNER_PARAMS_OVERRIDES = {
    "hma_pol_bars": 5,
    "sig_extreme": 60,
    "hw_extreme": 35,
    "mf_length": 31,
}

# Engine settings — preserve all 10 frontend blackout slots so the UI can render
# them. Mark the four active ones.
WINNER_BLACKOUTS = [
    {"active": False, "start_hour": 0,  "start_minute": 0,  "end_hour": 0,  "end_minute": 5},
    {"active": False, "start_hour": 9,  "start_minute": 0,  "end_hour": 9,  "end_minute": 5},
    {"active": False, "start_hour": 12, "start_minute": 0,  "end_hour": 14, "end_minute": 0},
    {"active": False, "start_hour": 15, "start_minute": 30, "end_hour": 15, "end_minute": 35},
    {"active": False, "start_hour": 16, "start_minute": 30, "end_hour": 22, "end_minute": 0},
    {"active": True,  "start_hour": 22, "start_minute": 0,  "end_hour": 23, "end_minute": 59},
    {"active": True,  "start_hour": 11, "start_minute": 0,  "end_hour": 14, "end_minute": 0},
    {"active": True,  "start_hour": 14, "start_minute": 30, "end_hour": 15, "end_minute": 0},
    {"active": True,  "start_hour": 6,  "start_minute": 0,  "end_hour": 9,  "end_minute": 0},
]

WINNER_RISK_DECIMAL = 0.0060
WINNER_NAME = "[WIN MNQ v6] HMASSLOsciV3 — MNQ 7m — WINNER (PnL $80.7k / DD $3.24k)"


def winner_engine_settings():
    return BacktestEngineSettings(
        auto_close_enabled=True,
        auto_close_hour=22,
        auto_close_minute=0,
        blackout_windows=[BlackoutWindowSettings(**w) for w in WINNER_BLACKOUTS],
        debug=False,
        daily_win_limit_enabled=False,
        daily_win_limit=500.0,
        daily_loss_limit_enabled=False,
        daily_loss_limit=700.0,
        daily_limit_mode="after_close",
    )


def winner_strategy_params():
    p = dict(SEED_PARAMS)
    p.update(WINNER_PARAMS_OVERRIDES)
    return p


if __name__ == "__main__":
    print("=" * 100)
    print("BUILD WINNER PRESET — TOP_C @ risk=0.60%")
    print("=" * 100)

    # Re-run the exact winner config first, with FULL preset params (including
    # all v3.1 new params at default) — same dict that will sit in the preset.
    final_params = winner_strategy_params()
    es = winner_engine_settings()

    res = run_backtest(
        strategy_name=STRATEGY,
        symbol=SYMBOL,
        interval=INTERVAL,
        start=START,
        end=END,
        initial_equity=INITIAL_EQUITY,
        risk_per_trade=WINNER_RISK_DECIMAL,
        max_contracts=MAX_CONTRACTS,
        strategy_params=final_params,
        engine_settings=es,
    )
    s = summarize(res)
    print(f"WINNER replay: {fmt_summary(s)}")
    print()

    preset = build_preset(
        strategy_name=STRATEGY,
        symbol=SYMBOL,
        interval=INTERVAL,
        start=START,
        end=END,
        initial_equity=INITIAL_EQUITY,
        risk_per_trade_decimal=WINNER_RISK_DECIMAL,
        max_contracts=MAX_CONTRACTS,
        strategy_param_overrides=final_params,
        engine_settings=es,
        metrics_summary=s,
        name=WINNER_NAME,
    )

    out_path = Path(__file__).resolve().parent.parent / "winner_preset.json"
    write_preset(preset, out_path, insert_into_presets_json=True)
    print(f"Wrote: {out_path}")
    print(f"Inserted into data/presets.json under name: {WINNER_NAME!r}")
    print()
    print("Expected metrics for verify_preset.py:")
    print(f"  net_pnl       = {s['net_pnl']}")
    print(f"  max_dd_$      = {s['max_dd_$']}")
    print(f"  trades        = {s['trades']}")
    print(f"  win_rate      = {s['win_rate']}")
    print(f"  profit_factor = {s['profit_factor']}")
