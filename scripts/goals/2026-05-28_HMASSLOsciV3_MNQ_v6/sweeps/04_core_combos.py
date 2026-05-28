"""Sweep 04 — combos of top picks from Sweep 03.

Best individual picks from 03:
  Pareto winners (strict):
    hma_pol_bars=5   → +$1,808 PnL / -$83 DD
    hma_pol_bars=3   → +$863 PnL / -$89 DD
    hw_extreme=35    → +$49 PnL / -$72 DD
  Best PnL (with worse DD):
    hma_pol_bars=2   → PnL=$66,141 / DD=$3,686
    hma1_len=15      → PnL=$65,526 / DD=$4,583
    sig_extreme=60   → PnL=$64,458 / DD=$3,557
  Best DD (with lower PnL):
    mf_length=31     → PnL=$59,075 / DD=$2,494 (DD valley)
    mf_length=29     → PnL=$57,132 / DD=$2,675
    entry_window=6   → PnL=$56,237 / DD=$3,091

Tests:
  A. Fine mf_length around 31 — find sharper valley
  B. Stack: hma_pol_bars × {3,5} × mf_length × {29,31,33,35} × {hw_extreme,sig_extreme}
  C. hma1_len=15 + hma_pol_bars + mf_length to see if hma1_len=15 PnL transfers
"""

from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1]))

from _shared.harness import bench  # noqa: E402
from _campaign import run_seed_kwargs, SEED_PARAMS  # noqa: E402


def run(label, params=None):
    return bench(label, **run_seed_kwargs(params=params))


def label(params):
    parts = []
    for k, v in params.items():
        parts.append(f"{k.split('_')[0]}={v}")
    return " ".join(parts).ljust(46)


if __name__ == "__main__":
    results = []
    seed = run("seed                                          ")
    results.append(seed)

    print()
    print("--- A. mf_length fine grid 23-35 ---")
    for v in [23, 27, 28, 30, 32]:  # the rest were tested in 03
        results.append(run(f"mf_length={v}".ljust(46),
                           params={"mf_length": v}))

    print()
    print("--- B. hma_pol_bars × mf_length (top Pareto × top DD) ---")
    for hpb in [3, 5]:
        for mfl in [29, 31, 33, 35, 37]:
            p = {"hma_pol_bars": hpb, "mf_length": mfl}
            results.append(run(label(p), params=p))

    print()
    print("--- C. hma_pol_bars=5 × sig_extreme/hw_extreme ---")
    for se in [45, 60]:
        for he in [25, 35]:
            p = {"hma_pol_bars": 5, "sig_extreme": se, "hw_extreme": he}
            results.append(run(label(p), params=p))

    print()
    print("--- D. hma1_len=15 cluster ---")
    for hpb in [0, 3, 5]:
        for mfl in [31, 35, 37]:
            p = {"hma1_len": 15, "hma_pol_bars": hpb, "mf_length": mfl}
            results.append(run(label(p), params=p))

    print()
    print("--- E. hma_pol_bars=5 + mf_length=31 + entry_window/cooldown ---")
    for ew in [2, 3, 4, 5, 6]:
        for cd in [3, 4, 6]:
            p = {"hma_pol_bars": 5, "mf_length": 31,
                 "entry_window_bars": ew, "cooldown_bars": cd}
            results.append(run(label(p), params=p))

    print()
    print("=" * 100)
    print("TOP-20 by PnL")
    print("=" * 100)
    for r in sorted(results, key=lambda x: -x["net_pnl"])[:20]:
        print(f"  {r['label']}  PnL=${r['net_pnl']:>9,.0f} | DD=${r['max_dd_$']:>6,.0f} | N={r['trades']}")

    print()
    print("STRICT PARETO  (PnL >= seed AND DD < seed)")
    found = False
    for r in results[1:]:
        if r["net_pnl"] >= seed["net_pnl"] and r["max_dd_$"] < seed["max_dd_$"]:
            print(f"  ✓ {r['label']}  PnL=${r['net_pnl']:>9,.0f} ({r['net_pnl']-seed['net_pnl']:+,.0f}) | "
                  f"DD=${r['max_dd_$']:>6,.0f} ({r['max_dd_$']-seed['max_dd_$']:+,.0f})")
            found = True
    if not found:
        print("  (none)")

    print()
    print("BIG-WIN PARETO (PnL within $5k of seed AND DD < seed - $500)")
    for r in results[1:]:
        if r["net_pnl"] >= seed["net_pnl"] - 5000 and r["max_dd_$"] < seed["max_dd_$"] - 500:
            print(f"  ✓ {r['label']}  PnL=${r['net_pnl']:>9,.0f} ({r['net_pnl']-seed['net_pnl']:+,.0f}) | "
                  f"DD=${r['max_dd_$']:>6,.0f} ({r['max_dd_$']-seed['max_dd_$']:+,.0f})")
