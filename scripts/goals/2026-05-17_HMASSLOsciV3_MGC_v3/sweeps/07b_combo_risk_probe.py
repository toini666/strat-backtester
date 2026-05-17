"""07b — Probe : ew=3 + hw_extreme=18 + risk push.

Both ew=3 and hw_extreme=18 are individually DD-reducers (DD ≈ $1,565 / $1,590
at risk 0.47%). The combo at low risk (sweep 05) gave $37,606 / $1,565 — no gain.
But under risk push, if DD compresses below the WINNER's $1,944, PnL may exceed
V2's $44,711.

Also probe B r=0.0057 (between 0.0055 pass and 0.0058 near-miss).

Sims used: ~9 / 200 → cumulative ~189/200
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


def main():
    results = []

    print("=" * 80)
    print("07b-1 — ew=3 + hw_extreme=18 + risk push")
    print("=" * 80)
    overr = {"entry_window_bars": 3, "hw_extreme": 18}
    for r in [0.0048, 0.0052, 0.0056, 0.0058, 0.0060, 0.0062]:
        results.append(_run(f"ew3+hwe18 r={r:.4f}", overr, [], r))

    print()
    print("=" * 80)
    print("07b-2 — B r=0.0057 (between 0.0055 pass and 0.0058 near-miss)")
    print("=" * 80)
    results.append(_run("B r=0.0057", {"entry_window_bars": 3}, [], 0.0057))

    print()
    print("=" * 80)
    print("07b-3 — C r=0.0058 + hw_extreme=18 (could compress DD into pass)")
    print("=" * 80)
    results.append(_run("C+hwe18 r=0.0058", {"entry_window_bars": 3, "hw_extreme": 18}, [(21, 0, 22, 0)], 0.0058))

    print()
    print("=" * 80)
    print("ALL — DD<2000 sorted by PnL")
    print("=" * 80)
    safe = [r for r in results if r["max_dd_$"] < 2_000]
    safe.sort(key=lambda r: r["net_pnl"], reverse=True)
    for r in safe:
        ratio = pdd(r["net_pnl"], r["max_dd_$"])
        margin = 2_000 - r["max_dd_$"]
        print(f"  {r['label']:<35} PnL=${r['net_pnl']:>9,.0f} DD=${r['max_dd_$']:>6,.0f} (margin ${margin:>4,.0f}) P/DD={ratio:.2f}")

    print()
    print("ALL — failures (DD>=2000)")
    for r in [x for x in results if x["max_dd_$"] >= 2_000]:
        print(f"  ❌ {r['label']:<35} PnL=${r['net_pnl']:>9,.0f} DD=${r['max_dd_$']:>6,.0f}")


if __name__ == "__main__":
    main()
