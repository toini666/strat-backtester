"""07c — Try to strictly beat V2 PnL $44,711 under DD<$2,000.

Current WINNER A r=0.0052 is $44,692 (tie with V2). Probe shaves to A r=0.0054
($45,141 / $2,062 ❌) — need to shave $62+ of DD to unlock.

Probe DD-reducers stacked on A r=0.0054:
  - tick_buffer=2 (DD reducer at low risk)
  - additional blackout candidates not yet tried (BO 22-23, BO 13-14, etc.)
  - cooldown_bars=3 (slight DD shave)

Sims used: ~10 / 200 → cumulative ~198/200
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

    # baseline to compare against
    print("Reference points:")
    results.append(_run("WINNER A r=0.0052", {}, [], 0.0052))
    results.append(_run("A r=0.0054 (fail $62)", {}, [], 0.0054))

    print()
    print("=" * 80)
    print("07c-1 — A r=0.0054 + single DD-reducer")
    print("=" * 80)
    results.append(_run("A r=0.0054 + tb=2",       {"tick_buffer": 2}, [], 0.0054))
    results.append(_run("A r=0.0054 + cd=3",       {"cooldown_bars": 3}, [], 0.0054))
    results.append(_run("A r=0.0054 + hw_ext=22",  {"hw_extreme": 22}, [], 0.0054))
    results.append(_run("A r=0.0054 + hma_pol=4",  {"hma_pol_bars": 4}, [], 0.0054))

    print()
    print("=" * 80)
    print("07c-2 — A r=0.0054 + unexplored blackouts")
    print("=" * 80)
    results.append(_run("A r=0.0054 + BO 22-23", {}, [(22, 0, 23, 0)], 0.0054))
    results.append(_run("A r=0.0054 + BO 02-03", {}, [(2, 0, 3, 0)], 0.0054))
    results.append(_run("A r=0.0054 + BO 13-14", {}, [(13, 0, 14, 0)], 0.0054))
    results.append(_run("A r=0.0054 + BO 18-19", {}, [(18, 0, 19, 0)], 0.0054))
    results.append(_run("A r=0.0054 + BO 19-20", {}, [(19, 0, 20, 0)], 0.0054))

    print()
    print("=" * 80)
    print("WINNERS — DD<2000 sorted by PnL")
    print("=" * 80)
    safe = [r for r in results if r["max_dd_$"] < 2_000]
    safe.sort(key=lambda r: r["net_pnl"], reverse=True)
    for r in safe:
        ratio = pdd(r["net_pnl"], r["max_dd_$"])
        margin = 2_000 - r["max_dd_$"]
        beat = "🏆" if r["net_pnl"] > 44_711 else "  "
        print(f"  {beat} {r['label']:<40} PnL=${r['net_pnl']:>9,.0f} DD=${r['max_dd_$']:>6,.0f} (margin ${margin:>4,.0f}) P/DD={ratio:.2f}")

    print()
    print("ALL — failures")
    for r in [x for x in results if x["max_dd_$"] >= 2_000]:
        print(f"  ❌ {r['label']:<40} PnL=${r['net_pnl']:>9,.0f} DD=${r['max_dd_$']:>6,.0f}")


if __name__ == "__main__":
    main()
