"""Phase 4 — Combine the Phase 3 winners (hw_extreme, rob_off, sig_extreme).

Best individual contributions on rr2.5/gap9 stack:
  hw_extreme_filter_on=True   → P/DD=8.16  PnL=$31,252 DD=$3,831
  rob_on=False                 → P/DD=6.20  PnL=$23,111 DD=$3,729
  sig_extreme_filter_on=True   → P/DD=4.28  PnL=$18,731 DD=$4,381
  tick_buffer=0                → P/DD=4.64  PnL=$20,499 DD=$4,422

Also try hw_extreme threshold variations and a few extra small-pts variations.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from scripts.goals._shared.harness import bench

from _campaign import (
    BASELINE_PARAMS,
    END,
    INITIAL_EQUITY,
    INTERVAL,
    MAX_CONTRACTS,
    RISK_PER_TRADE,
    START,
    STRATEGY,
    SYMBOL,
    baseline_engine,
)


PHASE2_WINNER = dict(BASELINE_PARAMS)
PHASE2_WINNER["min_gap"] = 9
PHASE2_WINNER["rr_tp"] = 2.5
PHASE2_WINNER["tick_buffer"] = 0


def _common():
    return dict(
        strategy_name=STRATEGY,
        symbol=SYMBOL,
        interval=INTERVAL,
        start=START,
        end=END,
        initial_equity=INITIAL_EQUITY,
        risk_per_trade=RISK_PER_TRADE,
        max_contracts=MAX_CONTRACTS,
        engine_settings=baseline_engine(),
    )


def _ovr(**kw):
    p = dict(PHASE2_WINNER)
    p.update(kw)
    return p


def main() -> int:
    print("=" * 100)
    print("PHASE 4 — Combo of Phase 3 winners")
    print("=" * 100)

    t0 = time.time()
    results = []

    results.append(("Phase-2 base (gap9 rr2.5 tb0)", bench("Phase-2 base", strategy_params=PHASE2_WINNER, **_common())))

    print()
    print("-" * 100)
    print("PRIMARY COMBOS (the big levers)")
    print("-" * 100)
    primary = [
        ("hw_ext=ON",                                   {"hw_extreme_filter_on": True}),
        ("rob=off",                                     {"rob_on": False}),
        ("sig_ext=ON",                                  {"sig_extreme_filter_on": True}),
        ("hw_ext=ON + rob=off",                         {"hw_extreme_filter_on": True, "rob_on": False}),
        ("hw_ext=ON + sig_ext=ON",                      {"hw_extreme_filter_on": True, "sig_extreme_filter_on": True}),
        ("rob=off + sig_ext=ON",                        {"rob_on": False, "sig_extreme_filter_on": True}),
        ("hw_ext=ON + rob=off + sig_ext=ON",            {"hw_extreme_filter_on": True, "rob_on": False, "sig_extreme_filter_on": True}),
    ]
    for label, kw in primary:
        s = bench(label, strategy_params=_ovr(**kw), **_common())
        results.append((label, s))

    print()
    print("-" * 100)
    print("hw_extreme threshold sweep (best stack so far)")
    print("-" * 100)
    base_kw = {"hw_extreme_filter_on": True, "rob_on": False, "sig_extreme_filter_on": True}
    for v in [10.0, 15.0, 18.0, 20.0, 22.0, 25.0, 30.0, 40.0]:
        kw = dict(base_kw); kw["hw_extreme"] = v
        s = bench(f"hw_extreme={v}", strategy_params=_ovr(**kw), **_common())
        results.append((f"hw_extreme={v}", s))

    print()
    print("-" * 100)
    print("Also test best 2-combo without sig_ext (might be better)")
    print("-" * 100)
    base_kw2 = {"hw_extreme_filter_on": True, "rob_on": False}
    for v in [15.0, 18.0, 20.0, 22.0, 25.0, 30.0]:
        kw = dict(base_kw2); kw["hw_extreme"] = v
        s = bench(f"(no_sig_ext) hw_extreme={v}", strategy_params=_ovr(**kw), **_common())
        results.append((f"(no_sig_ext) hw_extreme={v}", s))

    print()
    print("-" * 100)
    print("Check stc/ut at the new stack")
    print("-" * 100)
    base_kw = {"hw_extreme_filter_on": True, "rob_on": False, "sig_extreme_filter_on": True}
    test_modules = [
        ("baseline (3-combo)", base_kw),
        ("3-combo + stc=off", {**base_kw, "stc_on": False}),
        ("3-combo + ut=off", {**base_kw, "ut_on": False}),
        ("3-combo + hma=off", {**base_kw, "hma_on": False}),
        ("3-combo + ema=off", {**base_kw, "ema_on": False}),
        ("3-combo + st=off", {**base_kw, "st_on": False}),
        ("3-combo + alligator=off", {**base_kw, "alligator_on": False}),
        ("3-combo + osc=off", {**base_kw, "osc_on": False}),
    ]
    for label, kw in test_modules:
        s = bench(label, strategy_params=_ovr(**kw), **_common())
        results.append((label, s))

    elapsed = time.time() - t0
    print()
    print(f"Total: {len(results)} sims in {elapsed:.0f}s")

    print()
    print("=" * 100)
    print("Top 15 by P/DD ratio")
    print("=" * 100)
    for l, s in sorted(results, key=lambda x: -x[1]["net_pnl"] / max(x[1]["max_dd_$"], 1.0))[:15]:
        ratio = s["net_pnl"] / max(s["max_dd_$"], 1.0)
        print(f"  P/DD={ratio:>5.2f}  PnL=${s['net_pnl']:>7,.0f}  DD=${s['max_dd_$']:>5,.0f}  N={s['trades']:>4}  WR={s['win_rate']:.1f}%  ← {l}")

    print()
    print("=" * 100)
    print("Top 15 by absolute PnL")
    print("=" * 100)
    for l, s in sorted(results, key=lambda x: -x[1]["net_pnl"])[:15]:
        ratio = s["net_pnl"] / max(s["max_dd_$"], 1.0)
        print(f"  PnL=${s['net_pnl']:>7,.0f}  DD=${s['max_dd_$']:>5,.0f}  P/DD={ratio:>4.2f}  N={s['trades']:>4}  ← {l}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
