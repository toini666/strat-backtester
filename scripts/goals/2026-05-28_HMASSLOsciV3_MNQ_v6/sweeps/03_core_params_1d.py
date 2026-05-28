"""Sweep 03 — re-sweep core strategy params 1-D around the seed.

Seed:
  ema_len=11, hma1=13, hma2=21, amp_mult=2, hma_pol_bars=0,
  entry_window_bars=3, ssl_len=80, ssl_mult=0.2,
  hyper_wave_length=7, signal_length=4, mf_length=37, mf_smooth=7,
  sig_extreme=40, hw_extreme=20,
  cooldown_bars=3, max_candle_pct=0.9, tick_buffer=0

Memory hint: mf_length is non-monotone on HMASSLOsciV3 → fine grid.

Sims: ~70
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


SWEEPS = {
    "ema_len":            [5, 7, 9, 13, 15, 18, 21],
    "hma1_len":           [9, 11, 15, 17, 21],
    "hma2_len":           [13, 17, 25, 29, 34],
    "amp_mult":           [1.0, 1.5, 2.5, 3.0],
    "hma_pol_bars":       [2, 3, 5, 8],
    "entry_window_bars":  [1, 2, 4, 5, 6, 8],
    "ssl_len":            [40, 50, 60, 70, 90, 100],
    "ssl_mult":           [0.1, 0.15, 0.25, 0.3, 0.4],
    "hyper_wave_length":  [3, 4, 5, 6, 8, 9, 10],
    "signal_length":      [2, 3, 5, 6, 7],
    "mf_length":          [21, 25, 29, 31, 33, 35, 39, 41, 45, 49],  # fine, non-monotone
    "mf_smooth":          [3, 4, 5, 6, 8, 9, 10],
    "sig_extreme":        [25, 30, 35, 45, 50, 60],
    "hw_extreme":         [10, 15, 25, 30, 35],
    "cooldown_bars":      [0, 1, 2, 4, 5, 6],
    "max_candle_pct":     [0.0, 0.3, 0.5, 0.7, 1.0],
    "tick_buffer":        [1, 2, 3, 4],
}


if __name__ == "__main__":
    seed = run("seed                                          ")
    results = [seed]

    for param, values in SWEEPS.items():
        print()
        print(f"--- {param} ---")
        for v in values:
            label = f"{param}={v!r}".ljust(46)
            r = run(label, params={param: v})
            results.append(r)

    print()
    print("=" * 100)
    print("TOP-20 by PnL")
    print("=" * 100)
    for r in sorted(results, key=lambda x: -x["net_pnl"])[:20]:
        print(f"  {r['label']}  PnL=${r['net_pnl']:>9,.0f} | DD=${r['max_dd_$']:>6,.0f} | N={r['trades']}")

    print()
    print("=" * 100)
    print("TOP-15 by DD (lowest, with PnL >= seed - 5000)")
    print("=" * 100)
    pnl_floor = seed["net_pnl"] - 5000
    qualified = [r for r in results if r["net_pnl"] >= pnl_floor]
    for r in sorted(qualified, key=lambda x: x["max_dd_$"])[:15]:
        print(f"  {r['label']}  PnL=${r['net_pnl']:>9,.0f} | DD=${r['max_dd_$']:>6,.0f} | N={r['trades']}")

    print()
    print("=" * 100)
    print("STRICT PARETO  (PnL >= seed AND DD < seed)")
    print("=" * 100)
    found = False
    for r in results[1:]:
        if r["net_pnl"] >= seed["net_pnl"] and r["max_dd_$"] < seed["max_dd_$"]:
            print(f"  ✓ {r['label']}  PnL=${r['net_pnl']:>9,.0f} ({r['net_pnl']-seed['net_pnl']:+,.0f}) | "
                  f"DD=${r['max_dd_$']:>6,.0f} ({r['max_dd_$']-seed['max_dd_$']:+,.0f})")
            found = True
    if not found:
        print("  (none)")

    print()
    print("=" * 100)
    print("RELAXED PARETO  (PnL >= seed - $2k AND DD < seed - $200)")
    print("=" * 100)
    for r in results[1:]:
        if r["net_pnl"] >= seed["net_pnl"] - 2000 and r["max_dd_$"] < seed["max_dd_$"] - 200:
            print(f"  ✓ {r['label']}  PnL=${r['net_pnl']:>9,.0f} ({r['net_pnl']-seed['net_pnl']:+,.0f}) | "
                  f"DD=${r['max_dd_$']:>6,.0f} ({r['max_dd_$']-seed['max_dd_$']:+,.0f})")
