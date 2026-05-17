"""03 — Fine grid around cloud=T mf=30 ms=5 winner.

Test mf finer (27..33) and ms finer (3..6).
Also test interaction with cloud_zero_on and delta_ext_on.

Sims used: ~20 / 200 → cumulative ~37/200
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


CLOUD_BASE = dict(V2_WINNER_OVERRIDES)
CLOUD_BASE.update({"cloud_on": True, "mf_length": 30, "mf_smooth": 5})


def _es():
    return make_engine_settings(
        STRATEGY,
        extra_active_windows=[
            {"start_hour": sh, "start_minute": sm, "end_hour": eh, "end_minute": em}
            for (sh, sm, eh, em) in V2_WINNER_BLACKOUTS
        ],
    )


def _run(label, overrides, risk=V2_WINNER_RISK):
    p = dict(CLOUD_BASE)
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
    print("03-A — mf fine grid (cloud=T, ms=5)")
    print("=" * 80)
    for mf in [27, 28, 29, 30, 31, 32, 33]:
        results.append(_run(f"cloud=T mf={mf:>2} ms=5", {"mf_length": mf}))

    print()
    print("=" * 80)
    print("03-B — ms fine grid (cloud=T, mf=30)")
    print("=" * 80)
    for ms in [3, 4, 5, 6]:
        results.append(_run(f"cloud=T mf=30 ms={ms}", {"mf_smooth": ms}))

    print()
    print("=" * 80)
    print("03-C — interaction with cloud_zero_on / delta_ext_on")
    print("=" * 80)
    results.append(_run("cloud=T mf=30 ms=5 + cloud_zero_on=T", {"cloud_zero_on": True}))
    results.append(_run("cloud=T mf=30 ms=5 + delta_ext_on=T",  {"delta_ext_on": True}))
    results.append(_run("cloud=T mf=30 ms=5 + both_on",         {"cloud_zero_on": True, "delta_ext_on": True}))
    results.append(_run("cloud=T mf=30 ms=5 + hw_dir_on=F",     {"hw_dir_on": False}))
    results.append(_run("cloud=T mf=30 ms=5 + sig_extreme_on=F",{"sig_extreme_on": False}))
    results.append(_run("cloud=T mf=30 ms=5 + hw_extreme_on=F", {"hw_extreme_on": False}))

    print()
    print("=" * 80)
    print("TOP 10 (by ratio)")
    print("=" * 80)
    results.sort(key=lambda r: pdd(r["net_pnl"], r["max_dd_$"]), reverse=True)
    for r in results[:10]:
        ratio = pdd(r["net_pnl"], r["max_dd_$"])
        passed = "✅" if (r["net_pnl"] > 30_000 and r["max_dd_$"] < 2_000) else " "
        print(f"  {passed} {r['label']:<45} PnL=${r['net_pnl']:>9,.0f} DD=${r['max_dd_$']:>6,.0f} P/DD={ratio:.2f}")


if __name__ == "__main__":
    main()
