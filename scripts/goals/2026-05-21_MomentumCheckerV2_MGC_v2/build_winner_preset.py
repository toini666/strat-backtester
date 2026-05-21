"""Build the v2 MGC winner / robust / min-DD presets and insert into data/presets.json.

WINNER (MAX-PNL respecting $2,500):
  seed + BO 15:30-17 added + max_candle_pct=0.25 @ risk=0.55%
  → PnL=$58,625 / DD=$2,434 / N=810 / WR=39.6% / PF=1.58

ALT_ROBUST (more margin under $2,500):
  same params + risk=0.530%
  → PnL=$56,275 / DD=$2,135 / N=810 / WR=39.6% / PF=1.57

ALT_MINDD (closest to $2,000 floor):
  sl_max=80, max_candle_pct=0.22, BO 15:30-17, risk=0.530%
  → PnL=$51,909 / DD=$2,097 / N=806 / WR=39.3% / PF=1.53
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

CAMPAIGN_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(CAMPAIGN_DIR / "sweeps"))

from scripts.goals._shared.harness import run_backtest, summarize, fmt_summary  # noqa: E402
from scripts.goals._shared.preset import build_preset, write_preset  # noqa: E402

from _campaign import (  # noqa: E402
    BASELINE_PARAMS, END, INITIAL_EQUITY, INTERVAL, MAX_CONTRACTS,
    START, STRATEGY, SYMBOL, build_engine,
)


# Surgical blackouts: seed BO + added 15:30-17 window (Phase 7 finding)
WINNING_WINDOWS = [
    (12, 30, 14, 0),
    (15, 30, 17, 0),
    (18, 0, 19, 0),
    (20, 0, 21, 0),
    (22, 0, 23, 59),
]


def build(name_suffix, overrides, risk, expected, json_filename):
    engine = build_engine(WINNING_WINDOWS)
    params = dict(BASELINE_PARAMS)
    params.update(overrides)
    print(f"\n--- {name_suffix} ---")
    r = run_backtest(
        strategy_name=STRATEGY, symbol=SYMBOL, interval=INTERVAL,
        start=START, end=END,
        strategy_params=params,
        initial_equity=INITIAL_EQUITY,
        risk_per_trade=risk,
        max_contracts=MAX_CONTRACTS,
        engine_settings=engine,
    )
    s = summarize(r)
    print(fmt_summary(s))
    print(f"max_dd_pct: {r['metrics']['max_drawdown']:.2f}%")
    pnl_delta = s["net_pnl"] - expected["net_pnl"]
    dd_delta = s["max_dd_$"] - expected["max_dd_$"]
    print(f"Delta vs expected: PnL {pnl_delta:+,.0f} / DD {dd_delta:+,.0f}")

    preset = build_preset(
        strategy_name=STRATEGY, symbol=SYMBOL, interval=INTERVAL,
        start=START, end=END,
        initial_equity=INITIAL_EQUITY,
        risk_per_trade_decimal=risk,
        max_contracts=MAX_CONTRACTS,
        strategy_param_overrides=params,
        engine_settings=engine,
        metrics_summary=s,
        name=name_suffix,
    )

    out = CAMPAIGN_DIR / json_filename
    write_preset(preset, out, insert_into_presets_json=True)
    print(f"Wrote {out.name}; inserted in data/presets.json")
    return s


def main() -> int:
    print("=" * 110)
    print("BUILD PRESETS — v2 MGC MomentumCheckerV2 winners")
    print("=" * 110)

    # --- WINNER (MAX-PNL strictly respecting $2,500) ---
    build(
        name_suffix=(
            "[Auto] MomentumCheckerV2 — MGC 7m v2 — WINNER "
            "(PnL $58.6k / DD $2.43k / P/DD 24.1)"
        ),
        overrides={"max_candle_pct": 0.25},
        risk=0.0055,
        expected={"net_pnl": 58_625.0, "max_dd_$": 2_434.0},
        json_filename="winner_preset.json",
    )

    # --- ALT_ROBUST (more margin) ---
    build(
        name_suffix=(
            "[Auto] MomentumCheckerV2 — MGC 7m v2 — ROBUST "
            "(PnL $56.3k / DD $2.14k / P/DD 26.3)"
        ),
        overrides={"max_candle_pct": 0.25},
        risk=0.0053,
        expected={"net_pnl": 56_275.0, "max_dd_$": 2_135.0},
        json_filename="alt_robust_preset.json",
    )

    # --- ALT_MINDD (closest to $2,000 floor, Pareto-dominant) ---
    build(
        name_suffix=(
            "[Auto] MomentumCheckerV2 — MGC 7m v2 — MIN-DD "
            "(PnL $55.1k / DD $2.12k / P/DD 26.0)"
        ),
        overrides={"max_candle_pct": 0.25, "sl_max_points": 80.0},
        risk=0.0053,
        expected={"net_pnl": 55_054.0, "max_dd_$": 2_117.0},
        json_filename="alt_mindd_preset.json",
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())
