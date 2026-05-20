"""Phase 4 — Stack filter / module winners.

Phase 3 winners stack: min_gap=8, sl_lookback=15, rr_tp=3.0, sl_max=50.
Module / filter improvements found in Phase 3 (each tried individually):
- ut_on=False               P/DD 10.89  PnL=$40.5k DD=$3.7k
- sig_extreme_filter_on=ON  P/DD 10.30  PnL=$37.6k DD=$3.7k
- stc_on=False              P/DD  9.45  PnL=$34.6k DD=$3.7k
- rob_on=False              P/DD  8.97  PnL=$40.0k DD=$4.5k
- hw_extreme_filter_on=ON   P/DD  7.99  PnL=$36.4k DD=$4.6k
- use_heikin_ashi=True      P/DD  9.03  PnL=$39.3k DD=$4.3k

Combine pairs / triples and look for compound gains.
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


PHASE3_BASE = dict(BASELINE_PARAMS)
PHASE3_BASE.update({
    "min_gap": 8,
    "sl_lookback": 15,
    "rr_tp": 3.0,
    "sl_max_points": 50.0,
})


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
    p = dict(PHASE3_BASE)
    p.update(kw)
    return p


def main() -> int:
    print("=" * 100)
    print("PHASE 4 — Stack filter/module winners on Phase 3 base")
    print("=" * 100)

    t0 = time.time()
    results = []
    base = bench("Phase-3 base (rr=3.0+slMax=50)", strategy_params=PHASE3_BASE, **_common())
    results.append(("Phase-3 base", base))

    pairs = [
        # Pair stacks
        ("ut=off + sig_ext=ON",
            {"ut_on": False, "sig_extreme_filter_on": True}),
        ("ut=off + rob=off",
            {"ut_on": False, "rob_on": False}),
        ("ut=off + stc=off",
            {"ut_on": False, "stc_on": False}),
        ("ut=off + hw_ext=ON",
            {"ut_on": False, "hw_extreme_filter_on": True}),
        ("ut=off + heikin=ON",
            {"ut_on": False, "use_heikin_ashi": True}),
        ("sig_ext=ON + stc=off",
            {"sig_extreme_filter_on": True, "stc_on": False}),
        ("sig_ext=ON + rob=off",
            {"sig_extreme_filter_on": True, "rob_on": False}),
        ("sig_ext=ON + hw_ext=ON",
            {"sig_extreme_filter_on": True, "hw_extreme_filter_on": True}),
        ("rob=off + stc=off",
            {"rob_on": False, "stc_on": False}),
        ("rob=off + hw_ext=ON",
            {"rob_on": False, "hw_extreme_filter_on": True}),
        # Triple stacks
        ("ut=off + sig_ext=ON + rob=off",
            {"ut_on": False, "sig_extreme_filter_on": True, "rob_on": False}),
        ("ut=off + sig_ext=ON + stc=off",
            {"ut_on": False, "sig_extreme_filter_on": True, "stc_on": False}),
        ("ut=off + sig_ext=ON + hw_ext=ON",
            {"ut_on": False, "sig_extreme_filter_on": True, "hw_extreme_filter_on": True}),
        ("ut=off + rob=off + stc=off",
            {"ut_on": False, "rob_on": False, "stc_on": False}),
        # Quad
        ("ut=off + sig_ext=ON + rob=off + stc=off",
            {"ut_on": False, "sig_extreme_filter_on": True, "rob_on": False, "stc_on": False}),
        ("ut=off + sig_ext=ON + rob=off + hw_ext=ON",
            {"ut_on": False, "sig_extreme_filter_on": True, "rob_on": False, "hw_extreme_filter_on": True}),
        # Try slightly different rr after stacking
        ("ut=off + sig_ext=ON + rr=2.5",
            {"ut_on": False, "sig_extreme_filter_on": True, "rr_tp": 2.5}),
        ("ut=off + sig_ext=ON + rr=3.5",
            {"ut_on": False, "sig_extreme_filter_on": True, "rr_tp": 3.5}),
        ("ut=off + sig_ext=ON + rr=4.0",
            {"ut_on": False, "sig_extreme_filter_on": True, "rr_tp": 4.0}),
        # Variations on hw_extreme threshold
        ("ut=off + sig_ext=ON + hw_extreme=15",
            {"ut_on": False, "sig_extreme_filter_on": True, "hw_extreme": 15.0}),
        ("ut=off + sig_ext=ON + hw_extreme=25",
            {"ut_on": False, "sig_extreme_filter_on": True, "hw_extreme": 25.0}),
        # min_gap=9 retest with the stack (gap was tested at base only)
        ("ut=off + sig_ext=ON + gap=9",
            {"ut_on": False, "sig_extreme_filter_on": True, "min_gap": 9}),
        ("ut=off + sig_ext=ON + gap=7",
            {"ut_on": False, "sig_extreme_filter_on": True, "min_gap": 7}),
    ]
    for label, kw in pairs:
        s = bench(label, strategy_params=_ovr(**kw), **_common())
        results.append((label, s))

    elapsed = time.time() - t0
    print()
    print(f"Total: {len(results)} sims in {elapsed:.0f}s")

    print()
    print("=" * 100)
    print("DD-VALID (≤$2,500) sorted by PnL")
    print("=" * 100)
    dd_valid = [(l, s) for l, s in results if s["max_dd_$"] <= 2500]
    for l, s in sorted(dd_valid, key=lambda x: -x[1]["net_pnl"])[:15]:
        ratio = s["net_pnl"] / max(s["max_dd_$"], 1.0)
        print(f"  PnL=${s['net_pnl']:>7,.0f}  DD=${s['max_dd_$']:>5,.0f}  P/DD={ratio:>5.2f}  N={s['trades']:>4}  WR={s['win_rate']:.1f}%  ← {l}")
    if not dd_valid:
        print("  (none)")

    print()
    print("=" * 100)
    print("Top 15 by P/DD ratio (any DD)")
    print("=" * 100)
    for l, s in sorted(results, key=lambda x: -x[1]["net_pnl"] / max(x[1]["max_dd_$"], 1.0))[:15]:
        ratio = s["net_pnl"] / max(s["max_dd_$"], 1.0)
        print(f"  P/DD={ratio:>5.2f}  PnL=${s['net_pnl']:>7,.0f}  DD=${s['max_dd_$']:>5,.0f}  N={s['trades']:>4}  WR={s['win_rate']:.1f}%  ← {l}")

    print()
    print("=" * 100)
    print("Top 15 by absolute PnL (any DD)")
    print("=" * 100)
    for l, s in sorted(results, key=lambda x: -x[1]["net_pnl"])[:15]:
        ratio = s["net_pnl"] / max(s["max_dd_$"], 1.0)
        print(f"  PnL=${s['net_pnl']:>7,.0f}  DD=${s['max_dd_$']:>5,.0f}  P/DD={ratio:>4.2f}  N={s['trades']:>4}  ← {l}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
