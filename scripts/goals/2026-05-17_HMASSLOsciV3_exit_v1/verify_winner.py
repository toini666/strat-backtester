"""verify_winner — required even when no winner exists.

This campaign produced no `winner_v<N+1>` preset (see REPORT § Verdict).
This script's role is therefore reduced to: replay both reference baselines
via the Lab class with all flags at default and verify the trades and metrics
still match the published V3 figures to the cent. If this ever stops printing
✅ MATCH, the Lab strategy or one of its helpers regressed; do not trust any
campaign-derived numbers until fixed.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent / "phase2_hypotheses"))

from scripts.goals._shared.harness import run_backtest, summarize, fmt_summary  # noqa: E402
from scripts.goals._shared.preset import engine_from_dict  # noqa: E402

from _shared import BASELINES, LAB_STRATEGY_NAME, load_preset, strategy_params  # noqa: E402


EXPECTED = {
    "MNQ_v5": {"net_pnl": 68_764.72, "max_dd_$": 1_578.98, "trades": 1241},
    "MGC_v3": {"net_pnl": 44_691.68, "max_dd_$": 1_943.84, "trades": 865},
}

TOL = 0.01


def main():
    print(f"\n{'='*80}")
    print("  verify_winner — Lab(defaults) == published V3 baselines  (tol $0.01)")
    print(f"{'='*80}\n")
    all_ok = True
    for asset, path in BASELINES.items():
        preset = load_preset(path)
        engine = engine_from_dict(preset["engineSettings"])
        p = strategy_params(preset)
        res = run_backtest(
            strategy_name=LAB_STRATEGY_NAME,
            symbol=preset["symbol"],
            interval=preset["interval"],
            start=preset["startDatetime"],
            end=preset["endDatetime"],
            strategy_params=p,
            initial_equity=preset["initialEquity"],
            risk_per_trade=preset["riskPerTrade"] / 100.0,
            max_contracts=preset["maxContracts"],
            engine_settings=engine,
        )
        s = summarize(res)
        e = EXPECTED[asset]
        ok = (abs(s["net_pnl"] - e["net_pnl"]) < TOL
              and abs(s["max_dd_$"] - e["max_dd_$"]) < TOL
              and s["trades"] == e["trades"])
        print(f"[{asset}]")
        print(f"  Lab:      {fmt_summary(s)}")
        print(f"  Expected: PnL=${e['net_pnl']:>8,.2f} DD=${e['max_dd_$']:>6,.2f} N={e['trades']}")
        print(f"  {'✅ MATCH' if ok else '❌ DIFF'}\n")
        all_ok = all_ok and ok
    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
