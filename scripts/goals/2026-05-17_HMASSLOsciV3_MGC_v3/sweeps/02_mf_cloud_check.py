"""02 — mf_length + cloud_on sanity check.

Goal: V2 REPORT.md claims mf_length is no-op when cloud_on=False (V2 winner case).
But V5 MNQ found mf_length non-monotone (cloud_on=True). Verify both:
 1. mf_length is indeed no-op at cloud_on=False on V2 winner
 2. cloud_on=True changes the game — sweep mf around it

Sims used: ~14 / 200 → cumulative 15/200
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from scripts.goals._shared.harness import bench  # noqa: E402
from scripts.goals._shared.engine_settings import make_engine_settings  # noqa: E402

from _campaign import (  # noqa: E402
    STRATEGY, SYMBOL, INTERVAL, START, END,
    INITIAL_EQUITY, MAX_CONTRACTS,
    V2_WINNER_OVERRIDES, V2_WINNER_RISK, V2_WINNER_BLACKOUTS,
    pdd,
)


def _es():
    return make_engine_settings(
        STRATEGY,
        extra_active_windows=[
            {"start_hour": sh, "start_minute": sm, "end_hour": eh, "end_minute": em}
            for (sh, sm, eh, em) in V2_WINNER_BLACKOUTS
        ],
    )


def _run(label, overrides, risk=V2_WINNER_RISK):
    p = dict(V2_WINNER_OVERRIDES)
    p.update(overrides)
    s = bench(
        label,
        strategy_name=STRATEGY, symbol=SYMBOL, interval=INTERVAL,
        start=START, end=END,
        strategy_params=p, initial_equity=INITIAL_EQUITY,
        risk_per_trade=risk, max_contracts=MAX_CONTRACTS,
        engine_settings=_es(),
    )
    return s


def main():
    results = []

    print("=" * 80)
    print("02-A — mf_length sweep with cloud_on=False (V2 baseline)")
    print("=" * 80)
    # V2 winner has mf_length=35. Test 20, 25, 30, 35, 40, 45.
    for mf in [20, 25, 30, 35, 40, 45]:
        results.append(_run(f"cloud=F mf={mf:>2} ms=6", {"mf_length": mf, "cloud_on": False}))

    print()
    print("=" * 80)
    print("02-B — Same with cloud_on=True")
    print("=" * 80)
    for mf in [20, 25, 30, 35, 40, 45]:
        results.append(_run(f"cloud=T mf={mf:>2} ms=6", {"mf_length": mf, "cloud_on": True}))

    print()
    print("=" * 80)
    print("02-C — best cloud=T mf with ms=4..8")
    print("=" * 80)
    # determine best cloud=T mf
    cloud_t_results = [r for r in results if r["label"].startswith("cloud=T")]
    cloud_t_results.sort(key=lambda r: pdd(r["net_pnl"], r["max_dd_$"]), reverse=True)
    best_mf = int(cloud_t_results[0]["label"].split("mf=")[1].split()[0].strip())
    print(f"(testing ms sweep around best mf={best_mf})")
    for ms in [4, 5, 7, 8]:
        results.append(_run(f"cloud=T mf={best_mf:>2} ms={ms}", {"mf_length": best_mf, "mf_smooth": ms, "cloud_on": True}))

    print()
    print("=" * 80)
    print("TOP 5 (by ratio)")
    print("=" * 80)
    results.sort(key=lambda r: pdd(r["net_pnl"], r["max_dd_$"]), reverse=True)
    for r in results[:5]:
        ratio = pdd(r["net_pnl"], r["max_dd_$"])
        print(f"  {r['label']:<35} PnL=${r['net_pnl']:>9,.0f} DD=${r['max_dd_$']:>6,.0f} P/DD={ratio:.2f}")


if __name__ == "__main__":
    main()
