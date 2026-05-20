"""Phase 3 — Combo of Phase 2 risk-geometry winners + module/filter triage
on top of the new working baseline min_gap=9, rr_tp=2.5.

Phase 2 winner: PnL=$19,997, DD=$5,269, P/DD=3.80.
Combine top tweaks (sl_lookback=10, max_candle=0.3, tick_buffer=0, sl_max=50)
then triage modules at that base.
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
    print("PHASE 3 — Combo + module triage on min_gap=9, rr_tp=2.5")
    print("=" * 100)

    t0 = time.time()
    results = []

    results.append(("Phase-2 winner", bench("Phase-2 winner", strategy_params=PHASE2_WINNER, **_common())))

    # ----- Risk-geom combos -----
    print()
    print("-" * 100)
    print("COMBO: stack top Phase-2 tweaks")
    print("-" * 100)
    combos = [
        ("rr2.5 + slLB=10",                   {"sl_lookback": 10}),
        ("rr2.5 + slMax=50",                  {"sl_max_points": 50.0}),
        ("rr2.5 + cnd=0.3",                   {"max_candle_pct": 0.3}),
        ("rr2.5 + tickBuf=0",                 {"tick_buffer": 0}),
        ("rr2.5 + slLB=10 + slMax=50",        {"sl_lookback": 10, "sl_max_points": 50.0}),
        ("rr2.5 + slLB=10 + cnd=0.3",         {"sl_lookback": 10, "max_candle_pct": 0.3}),
        ("rr2.5 + slLB=10 + tickBuf=0",       {"sl_lookback": 10, "tick_buffer": 0}),
        ("rr2.5 + slLB=10 + slMax=50 + cnd=0.3",   {"sl_lookback": 10, "sl_max_points": 50.0, "max_candle_pct": 0.3}),
        ("rr2.5 + slLB=10 + slMax=50 + cnd=0.3 + tb0", {"sl_lookback": 10, "sl_max_points": 50.0, "max_candle_pct": 0.3, "tick_buffer": 0}),
        # try rr=2.25 vs 2.75 with the stack
        ("rr2.25 + slLB=10 + cnd=0.3",        {"rr_tp": 2.25, "sl_lookback": 10, "max_candle_pct": 0.3}),
        ("rr2.75 + slLB=10 + cnd=0.3",        {"rr_tp": 2.75, "sl_lookback": 10, "max_candle_pct": 0.3}),
    ]
    for label, kw in combos:
        s = bench(label, strategy_params=_ovr(**kw), **_common())
        results.append((label, s))

    # ----- Module on/off triage at the current best stack -----
    # Pick the best combo from above to use as base for module triage
    best = max(results, key=lambda r: r[1]["net_pnl"] / max(r[1]["max_dd_$"], 1.0))
    best_label, best_s = best
    best_kw = dict(PHASE2_WINNER)
    for l, kw in [("",{})] + [(lbl, kw) for lbl, kw in combos]:
        if l == best_label:
            best_kw.update(kw)
            break

    # find best combo in results (need its kw)
    best_combo_kw = None
    for lbl, kw in combos:
        if lbl == best_label:
            best_combo_kw = kw
            break
    module_base = _ovr(**(best_combo_kw or {}))
    print()
    print("-" * 100)
    print(f"MODULE TRIAGE on best stack: {best_label}  (P/DD={best_s['net_pnl']/max(best_s['max_dd_$'],1):.2f})")
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
        params = dict(module_base)
        params[k] = v
        label = f"{k}={v}"
        s = bench(label, strategy_params=params, **_common())
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
