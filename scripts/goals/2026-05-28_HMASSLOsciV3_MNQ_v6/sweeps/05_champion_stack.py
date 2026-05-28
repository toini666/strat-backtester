"""Sweep 05 — explore around the new champion stack.

Champion from Sweep 04:
  hma_pol_bars=5 + sig_extreme=60 + hw_extreme=35
  → PnL=$68,107 (+$4,964) / DD=$3,376 (-$181)

Goals:
  A. Extend sig_extreme/hw_extreme range — does PnL keep rising?
  B. Add mf_length to the champion stack (DD-leaning variants).
  C. Add other knobs that were close to Pareto (hw_partial, signal_candle_sl_on,
     final_exit_mode, signal_length=5).
  D. Test sig_extreme_on=False / hw_extreme_on=False ("disable extremes").
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


CHAMP = {"hma_pol_bars": 5, "sig_extreme": 60, "hw_extreme": 35}


def with_champ(extra):
    p = dict(CHAMP)
    p.update(extra)
    return p


def label(p):
    return " ".join(f"{k.split('_')[0]}={v}" for k, v in p.items()).ljust(60)


if __name__ == "__main__":
    results = []
    seed = run("seed".ljust(60))
    results.append(seed)
    champ = run("CHAMP (hma=5 sig=60 hw=35)".ljust(60),
                params=CHAMP)
    results.append(champ)

    print()
    print("--- A. extend sig_extreme/hw_extreme grid around champ ---")
    for se in [50, 55, 65, 70, 80, 90]:
        for he in [30, 40, 50]:
            p = {"hma_pol_bars": 5, "sig_extreme": se, "hw_extreme": he}
            results.append(run(label(p), params=p))

    print()
    print("--- A2. extremes disabled ---")
    for cfg in [
        {"hma_pol_bars": 5, "sig_extreme_on": False},
        {"hma_pol_bars": 5, "hw_extreme_on": False},
        {"hma_pol_bars": 5, "sig_extreme_on": False, "hw_extreme_on": False},
    ]:
        results.append(run(label(cfg), params=cfg))

    print()
    print("--- B. champ + mf_length variations ---")
    for mfl in [25, 27, 29, 31, 33, 35, 39, 41]:
        p = with_champ({"mf_length": mfl})
        results.append(run(label(p), params=p))

    print()
    print("--- C. champ + final_exit_mode/final_exit_pct ---")
    for fep in [0.05, 0.08, 0.15]:
        p = with_champ({"final_exit_mode": "% du prix d'entrée en profit",
                        "final_exit_pct": fep})
        results.append(run(label(p), params=p))

    print()
    print("--- D. champ + cloud_on/delta_on variations ---")
    for cd in [
        {"cloud_on": False, "delta_on": True},
        {"cloud_on": True, "delta_on": False},
        {"cloud_on": False, "delta_on": False},
        {"cloud_zero_on": True},
    ]:
        p = with_champ(cd)
        results.append(run(label(p), params=p))

    print()
    print("--- E. champ + hw_partial_pct (TP1 partial) ---")
    for pp in [25.0, 50.0]:
        for rr in [0.0, 0.5, 1.0]:
            p = with_champ({"hw_partial_pct": pp, "hw_partial_min_rr": rr})
            results.append(run(label(p), params=p))

    print()
    print("=" * 100)
    print("TOP-20 by PnL")
    print("=" * 100)
    for r in sorted(results, key=lambda x: -x["net_pnl"])[:20]:
        print(f"  {r['label']}  PnL=${r['net_pnl']:>9,.0f} | DD=${r['max_dd_$']:>6,.0f} | N={r['trades']}")

    print()
    print("STRICT PARETO  (PnL > champ AND DD <= champ)")
    found = False
    for r in results[2:]:
        if r["net_pnl"] > champ["net_pnl"] and r["max_dd_$"] <= champ["max_dd_$"]:
            print(f"  ✓ {r['label']}  PnL=${r['net_pnl']:>9,.0f} ({r['net_pnl']-champ['net_pnl']:+,.0f}) | "
                  f"DD=${r['max_dd_$']:>6,.0f} ({r['max_dd_$']-champ['max_dd_$']:+,.0f})")
            found = True
    if not found:
        print("  (none)")

    print()
    print("BIG-DD CUT (PnL >= seed - $2k AND DD < $2,800)")
    for r in results[2:]:
        if r["net_pnl"] >= seed["net_pnl"] - 2000 and r["max_dd_$"] < 2800:
            print(f"  ✓ {r['label']}  PnL=${r['net_pnl']:>9,.0f} ({r['net_pnl']-seed['net_pnl']:+,.0f}) | "
                  f"DD=${r['max_dd_$']:>6,.0f} ({r['max_dd_$']-seed['max_dd_$']:+,.0f})")
