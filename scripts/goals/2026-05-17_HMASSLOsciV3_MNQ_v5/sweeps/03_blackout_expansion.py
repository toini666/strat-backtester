"""03 — Hour blackout expansion sweep.

V4 has BO 11-12 + 14-15 active. Baseline analysis shows still-toxic hours:
  H=08 = -$1,680 (n=69)  ← biggest untouched toxic
  H=12 = -$1,654 (n=81)  ← V4 BO covers 11-12 only, not 12-13
  H=04 = -$580  (n=54)
  H=06 = -$247  (n=45)

Single-hour adds and small expansion tests, then 2-hour combos. All on V4 base
config (ema=11, r=0.0036). Sort key: ratio + DD-under-2k.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _campaign as C  # noqa: E402

from scripts.goals._shared.harness import bench  # noqa: E402
from scripts.goals._shared.engine_settings import make_engine_settings  # noqa: E402


V4_BO = [(11, 12), (14, 15)]


def es_with(extra):
    """V4 BO + extra (list of (s, e) tuples)."""
    return make_engine_settings(
        C.STRATEGY,
        extra_active_windows=[C.window(s, e) for s, e in V4_BO + extra],
    )


def main():
    print("=== 03 — BLACKOUT EXPANSION ===\n")
    print("Base: V4 BO=11+14, ema=11, r=0.0036\n")
    results = []

    # (A) Single hour adds — test each toxic candidate alone
    print("[A] V4 BO + single-hour add:")
    for label, extra in [
        ("baseline V4 (control)", []),
        ("+H=08", [(8, 9)]),
        ("+H=12 (12-13)", [(12, 13)]),
        ("+H=04", [(4, 5)]),
        ("+H=06", [(6, 7)]),
        ("+H=23 (no auto-close)", [(23, 23, 59)] if False else [(23, 23)]),
    ]:
        if not extra:
            es = es_with([])
        else:
            es = es_with(extra)
        s = bench(
            f"  V4 BO {label}",
            strategy_name=C.STRATEGY, symbol=C.SYMBOL, interval=C.TF,
            start=C.START, end=C.END,
            strategy_params=dict(C.V4_WINNER_PARAMS),
            initial_equity=C.INITIAL_EQUITY,
            risk_per_trade=C.DEFAULT_RISK,
            max_contracts=C.MAX_CONTRACTS,
            engine_settings=es,
        )
        s["config"] = f"V4 BO {label}"
        results.append(s)

    # (B) Pair adds — combine the best 2 toxic adds
    print("\n[B] V4 BO + pair adds:")
    for label, extra in [
        ("+H=08+12", [(8, 9), (12, 13)]),
        ("+H=08+04", [(8, 9), (4, 5)]),
        ("+H=12+04", [(12, 13), (4, 5)]),
        ("+H=08+12+04", [(8, 9), (12, 13), (4, 5)]),
        ("+H=08+12+06", [(8, 9), (12, 13), (6, 7)]),
    ]:
        s = bench(
            f"  V4 BO {label}",
            strategy_name=C.STRATEGY, symbol=C.SYMBOL, interval=C.TF,
            start=C.START, end=C.END,
            strategy_params=dict(C.V4_WINNER_PARAMS),
            initial_equity=C.INITIAL_EQUITY,
            risk_per_trade=C.DEFAULT_RISK,
            max_contracts=C.MAX_CONTRACTS,
            engine_settings=es_with(extra),
        )
        s["config"] = f"V4 BO {label}"
        results.append(s)

    # (C) Wider variants of V4's own blackouts
    print("\n[C] Widening V4 blackouts themselves:")
    wider_combos = [
        ("BO 11-13 + 14-15", [(11, 13), (14, 15)]),       # extend 11-12 to 11-13
        ("BO 11-12 + 14-16", [(11, 12), (14, 16)]),       # extend 14-15 to 14-16
        ("BO 11-13 + 14-16", [(11, 13), (14, 16)]),       # extend both
        ("BO 10:30-12 + 14-15", [(10, 12, 30, 0), (14, 15)]),  # earlier start
    ]
    for label, extra in wider_combos:
        # build extra-active windows directly (not V4 BO + extra)
        es = make_engine_settings(
            C.STRATEGY,
            extra_active_windows=[C.window(*w) for w in extra],
        )
        s = bench(
            f"  {label}",
            strategy_name=C.STRATEGY, symbol=C.SYMBOL, interval=C.TF,
            start=C.START, end=C.END,
            strategy_params=dict(C.V4_WINNER_PARAMS),
            initial_equity=C.INITIAL_EQUITY,
            risk_per_trade=C.DEFAULT_RISK,
            max_contracts=C.MAX_CONTRACTS,
            engine_settings=es,
        )
        s["config"] = label
        results.append(s)

    # Summary
    print("\n=== SUMMARY ===")
    for s in results:
        s["ratio"] = round(s["net_pnl"] / s["max_dd_$"], 2) if s["max_dd_$"] > 0 else 0
        s["under_2k"] = "✅" if s["max_dd_$"] < C.TARGET_MAX_DD else "❌"
    results.sort(key=lambda s: s["ratio"], reverse=True)

    print(f"\n{'PASS':<5} {'RATIO':>6} {'PnL':>10} {'DD':>8} {'N':>5} {'WR':>6} {'PF':>5} {'CONFIG':<40}")
    print("-" * 100)
    for s in results:
        print(f"{s['under_2k']:<5} {s['ratio']:>6.2f} ${s['net_pnl']:>8,.0f} "
              f"${s['max_dd_$']:>6,.0f} {s['trades']:>5} {s['win_rate']:>5.1f}% "
              f"{s['profit_factor']:>5} {s['config']:<40}")

    return results


if __name__ == "__main__":
    main()
