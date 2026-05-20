"""Phase 3 — Combo Phase 2 winners + module triage.

Phase 2 best (P/DD): sl_lookback=15 → PnL=$41,915, DD=$5,725, P/DD=7.32.
Stack with the other strong Phase 2 levers (rr_tp=2.25-3.0, tick_buffer=1,
sl_max_points=50) then triage modules on/off.
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
PHASE2_WINNER["min_gap"] = 8
PHASE2_WINNER["sl_lookback"] = 15


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
    print("PHASE 3 — Combo + module triage on min_gap=8, sl_lookback=15")
    print("=" * 100)

    t0 = time.time()
    results = []
    results.append(("Phase-2 winner", bench("Phase-2 winner", strategy_params=PHASE2_WINNER, **_common())))

    print()
    print("-" * 100)
    print("COMBO: stack top Phase-2 tweaks (rr_tp, tick_buffer, sl_max, candle)")
    print("-" * 100)
    combos = [
        ("rr=2.25",                       {"rr_tp": 2.25}),
        ("rr=2.5",                        {"rr_tp": 2.5}),
        ("rr=2.75",                       {"rr_tp": 2.75}),
        ("rr=3.0",                        {"rr_tp": 3.0}),
        ("tb=1",                          {"tick_buffer": 1}),
        ("tb=3",                          {"tick_buffer": 3}),
        ("slMax=50",                      {"sl_max_points": 50.0}),
        ("cnd=0.3",                       {"max_candle_pct": 0.3}),
        ("rr=2.25 + slMax=50",            {"rr_tp": 2.25, "sl_max_points": 50.0}),
        ("rr=2.25 + tb=1",                {"rr_tp": 2.25, "tick_buffer": 1}),
        ("rr=2.5 + slMax=50",             {"rr_tp": 2.5, "sl_max_points": 50.0}),
        ("rr=2.5 + tb=1",                 {"rr_tp": 2.5, "tick_buffer": 1}),
        ("rr=3.0 + tb=1",                 {"rr_tp": 3.0, "tick_buffer": 1}),
        ("rr=3.0 + slMax=50",             {"rr_tp": 3.0, "sl_max_points": 50.0}),
        ("rr=2.5 + tb=1 + slMax=50",      {"rr_tp": 2.5, "tick_buffer": 1, "sl_max_points": 50.0}),
        ("rr=3.0 + tb=1 + slMax=50",      {"rr_tp": 3.0, "tick_buffer": 1, "sl_max_points": 50.0}),
        ("rr=2.5 + slLB=10",              {"rr_tp": 2.5, "sl_lookback": 10}),
        ("rr=3.0 + slLB=10",              {"rr_tp": 3.0, "sl_lookback": 10}),
        ("rr=3.0 + slLB=20",              {"rr_tp": 3.0, "sl_lookback": 20}),
    ]
    for label, kw in combos:
        s = bench(label, strategy_params=_ovr(**kw), **_common())
        results.append((label, s))

    # Pick best P/DD combo as base for module triage
    best = max(results, key=lambda r: r[1]["net_pnl"] / max(r[1]["max_dd_$"], 1.0))
    best_label, best_s = best
    best_kw = {}
    for lbl, kw in combos:
        if lbl == best_label:
            best_kw = kw
            break
    module_base_params = _ovr(**best_kw)
    print()
    print("-" * 100)
    print(f"MODULE TRIAGE on best stack: {best_label}  "
          f"(P/DD={best_s['net_pnl']/max(best_s['max_dd_$'],1):.2f}, "
          f"PnL=${best_s['net_pnl']:,.0f}, DD=${best_s['max_dd_$']:,.0f})")
    print("-" * 100)
    modules = [
        ("osc_on", False),
        ("ema_on", False),
        ("st_on", False),
        ("alligator_on", False),
        ("ut_on", False),
        ("rob_on", False),
        ("stc_on", False),
        ("hma_on", False),
        # filters within osc
        ("hw_filter_on", False),
        ("hw_extreme_filter_on", True),
        ("sig_extreme_filter_on", True),
        ("use_heikin_ashi", True),
    ]
    for k, v in modules:
        params = dict(module_base_params)
        params[k] = v
        label = f"{k}={v}"
        s = bench(label, strategy_params=params, **_common())
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
