"""Sweep 02 — focused combos of new v3.1 params with min_sl_points.

Sweep 01 showed:
  - entry_cross_mode=Baseline strictly dominates (other two hurt PnL).
  - ema_exit_ext_on=True hurts DD on every length tested.
  - min_sl_points trades PnL down for DD down, smooth monotone.

Goals here:
  A. Confirm ema_exit_ext_on is dominated even at low ema lengths combined with
     min_sl_points (does the EMA stay-in keep losers but the floor caps them?)
  B. Map min_sl_points more finely between 0-25 (the sweet spot for PnL/DD
     trade) with combinations on max_sl_points too (entry SL window is currently
     wide at 300).
  C. Test min_sl_points combined with one_trade_per_entry_window=False.

Sims: ~24
"""

from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1]))

from _shared.harness import bench  # noqa: E402
from _campaign import run_seed_kwargs  # noqa: E402


def run(label, params=None):
    return bench(label, **run_seed_kwargs(params=params))


if __name__ == "__main__":
    results = []

    print("=" * 100)
    print("SWEEP 02 — combos around min_sl_points + ema_exit_ext")
    print("=" * 100)

    seed = run("seed                                          ")
    results.append(seed)

    print()
    print("--- min_sl_points fine + max_sl_points narrower ---")
    for min_sl in [0, 3, 5, 8, 12, 18]:
        for max_sl in [200, 150, 100]:
            results.append(run(
                f"min={min_sl:>2d} max={max_sl:>3d}                          ",
                params={"min_sl_points": float(min_sl), "max_sl_points": float(max_sl)},
            ))

    print()
    print("--- min_sl + ema_exit_ext (does the floor cap the EMA stay-in losers?) ---")
    for min_sl in [15, 25, 40]:
        for ema_len in [5, 9]:
            results.append(run(
                f"min={min_sl:>2d} emaExt ON len={ema_len:<2d}                    ",
                params={
                    "min_sl_points": float(min_sl),
                    "ema_exit_ext_on": True,
                    "ema_exit_len": ema_len,
                },
            ))

    print()
    print("=" * 100)
    print("TOP-10 by PnL")
    print("=" * 100)
    for r in sorted(results, key=lambda x: -x["net_pnl"])[:10]:
        print(f"  {r['label']}  PnL=${r['net_pnl']:>9,.0f} | DD=${r['max_dd_$']:>6,.0f} | N={r['trades']}")

    print()
    print("PARETO  (PnL within $3k of seed AND DD < seed)")
    for r in results[1:]:
        if r["net_pnl"] >= seed["net_pnl"] - 3000 and r["max_dd_$"] < seed["max_dd_$"]:
            print(f"  ✓ {r['label']}  PnL=${r['net_pnl']:>9,.0f} ({r['net_pnl']-seed['net_pnl']:+,.0f}) | "
                  f"DD=${r['max_dd_$']:>6,.0f} ({r['max_dd_$']-seed['max_dd_$']:+,.0f})")

    print()
    print("RATIO PnL/DD  (top 10)")
    for r in sorted(results, key=lambda x: -x["net_pnl"]/x["max_dd_$"] if x["max_dd_$"]>0 else 0)[:10]:
        ratio = r["net_pnl"]/r["max_dd_$"] if r["max_dd_$"]>0 else 0
        print(f"  ratio={ratio:>5.2f}  {r['label']}  PnL=${r['net_pnl']:>9,.0f} | DD=${r['max_dd_$']:>6,.0f}")
