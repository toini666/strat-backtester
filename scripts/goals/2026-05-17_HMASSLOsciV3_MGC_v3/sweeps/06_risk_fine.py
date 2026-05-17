"""06 — Fine risk_per_trade sweep on best param + BO combos.

V5 MNQ insight: risk function is non-monotone (floor contracts).
Sweep r in 0.01% steps from 0.40% to 0.70% on 3 candidate bases:
  A: BASE (cloud=T mf=29 ms=5) + V2 BO only          (DD $1,813)
  B: BASE + ew=3 + V2 BO only                         (DD $1,565)
  C: BASE + ew=3 + V2 BO + BO 21-22                  (DD $1,565, PnL $40,138)

Sims used: ~50 / 200 → cumulative ~164/200
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
    V2_WINNER_OVERRIDES, V2_WINNER_BLACKOUTS,
    pdd,
)


CLOUD_BASE = dict(V2_WINNER_OVERRIDES)
CLOUD_BASE.update({"cloud_on": True, "mf_length": 29, "mf_smooth": 5})


def _es(extra_bos):
    return make_engine_settings(
        STRATEGY,
        extra_active_windows=[
            {"start_hour": sh, "start_minute": sm, "end_hour": eh, "end_minute": em}
            for (sh, sm, eh, em) in (list(V2_WINNER_BLACKOUTS) + list(extra_bos))
        ],
    )


def _run(label, overrides, extra_bos, risk):
    p = dict(CLOUD_BASE)
    p.update(overrides)
    s = bench(
        label,
        strategy_name=STRATEGY, symbol=SYMBOL, interval=INTERVAL,
        start=START, end=END,
        strategy_params=p, initial_equity=INITIAL_EQUITY,
        risk_per_trade=risk, max_contracts=MAX_CONTRACTS,
        engine_settings=_es(extra_bos),
    )
    return s


RISKS = [0.0040, 0.0042, 0.0044, 0.0046, 0.0048, 0.0050,
         0.0052, 0.0054, 0.0056, 0.0058, 0.0060, 0.0062,
         0.0064, 0.0066, 0.0068, 0.0070]


def main():
    results = []

    # CANDIDATE A — BASE (no ew=3, no extra BO)
    print("=" * 80)
    print("06-A — Risk sweep on BASE (cloud=T mf=29 ms=5)")
    print("=" * 80)
    for r in RISKS:
        results.append(_run(f"A r={r:.4f}", {}, [], r))

    # CANDIDATE B — BASE + ew=3
    print()
    print("=" * 80)
    print("06-B — Risk sweep on BASE + ew=3")
    print("=" * 80)
    for r in RISKS:
        results.append(_run(f"B r={r:.4f}", {"entry_window_bars": 3}, [], r))

    # CANDIDATE C — BASE + ew=3 + BO 21-22
    print()
    print("=" * 80)
    print("06-C — Risk sweep on BASE + ew=3 + BO 21-22")
    print("=" * 80)
    for r in RISKS:
        results.append(_run(f"C r={r:.4f}", {"entry_window_bars": 3}, [(21, 0, 22, 0)], r))

    print()
    print("=" * 80)
    print("TOP 20 by PnL (DD<2000 strict)")
    print("=" * 80)
    safe = [r for r in results if r["max_dd_$"] < 2_000]
    safe.sort(key=lambda r: r["net_pnl"], reverse=True)
    for r in safe[:20]:
        ratio = pdd(r["net_pnl"], r["max_dd_$"])
        margin = 2_000 - r["max_dd_$"]
        print(f"  {r['label']:<25} PnL=${r['net_pnl']:>9,.0f} DD=${r['max_dd_$']:>6,.0f} (margin ${margin:>4,.0f}) P/DD={ratio:.2f}")

    print()
    print("=" * 80)
    print("TOP 20 by P/DD (DD<2000 strict)")
    print("=" * 80)
    safe2 = sorted(safe, key=lambda r: pdd(r["net_pnl"], r["max_dd_$"]), reverse=True)
    for r in safe2[:20]:
        ratio = pdd(r["net_pnl"], r["max_dd_$"])
        print(f"  {r['label']:<25} PnL=${r['net_pnl']:>9,.0f} DD=${r['max_dd_$']:>6,.0f} P/DD={ratio:.2f}")


if __name__ == "__main__":
    main()
