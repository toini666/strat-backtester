"""Sweep 01 — new v3.1 params in 1-D, around the seed.

Levers:
  - entry_cross_mode: Baseline | Borne proche | Borne opposée (3 sims)
  - min_sl_points:    0, 5, 10, 15, 20, 30, 40, 50, 60, 80  (10 sims; 0 = seed)
  - ema_exit_ext_on=True × ema_exit_len: 5, 7, 9, 11, 15, 20, 30, 50 (8 sims)

Sims: 21 (3 - 1 baseline already in seed + 9 + 8 + seed)
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
    print("SWEEP 01 — new v3.1 params 1-D")
    print("=" * 100)

    # Seed reference
    results.append(run("seed                                      "))

    print()
    print("--- entry_cross_mode ---")
    for mode in ["Borne proche", "Borne opposée"]:
        results.append(run(f"entry_cross={mode:<15s}            ",
                           params={"entry_cross_mode": mode}))

    print()
    print("--- min_sl_points ---")
    for v in [5, 10, 15, 20, 30, 40, 50, 60, 80]:
        results.append(run(f"min_sl_points={v:<3d}                       ",
                           params={"min_sl_points": float(v)}))

    print()
    print("--- ema_exit_ext_on=True × ema_exit_len ---")
    for v in [5, 7, 9, 11, 15, 20, 30, 50]:
        results.append(run(f"ema_ext=ON ema_len={v:<3d}                ",
                           params={"ema_exit_ext_on": True, "ema_exit_len": v}))

    print()
    print("=" * 100)
    print("TOP-10 by PnL")
    print("=" * 100)
    for r in sorted(results, key=lambda x: -x["net_pnl"])[:10]:
        print(f"  {r['label']}  PnL=${r['net_pnl']:>9,.0f} | DD=${r['max_dd_$']:>6,.0f} | N={r['trades']}")

    print()
    print("TOP-10 by DD (lowest)")
    for r in sorted(results, key=lambda x: x["max_dd_$"])[:10]:
        print(f"  {r['label']}  PnL=${r['net_pnl']:>9,.0f} | DD=${r['max_dd_$']:>6,.0f} | N={r['trades']}")

    print()
    print("PARETO (PnL >= seed-2k AND DD < seed)")
    seed = results[0]
    for r in results[1:]:
        if r["net_pnl"] >= seed["net_pnl"] - 2000 and r["max_dd_$"] < seed["max_dd_$"]:
            print(f"  ✓ {r['label']}  PnL=${r['net_pnl']:>9,.0f} ({r['net_pnl']-seed['net_pnl']:+,.0f}) | "
                  f"DD=${r['max_dd_$']:>6,.0f} ({r['max_dd_$']-seed['max_dd_$']:+,.0f})")
