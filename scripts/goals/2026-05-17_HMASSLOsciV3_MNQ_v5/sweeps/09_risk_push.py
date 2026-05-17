"""09 — Risk push on the winner combo (mf=31 ms=7).

Winner: BASE_A mf=31 ms=7 r=0.0042 → $61,102 / $1,457 / margin $543.
Margin is HUGE — there's room to push risk. Find the DD-wall.

Test r in fine grid: 0.0043, 0.0044, 0.0046, 0.0048, 0.0050, 0.0055, 0.006 on both BASE_A and BASE_B.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _campaign as C  # noqa: E402

from scripts.goals._shared.harness import bench  # noqa: E402
from scripts.goals._shared.engine_settings import make_engine_settings  # noqa: E402


BASE_A = [(11, 12), (14, 15), (8, 9), (12, 13)]
BASE_B = [(11, 12), (14, 15), (8, 9), (12, 13), (4, 5)]


def es_for(bo):
    return make_engine_settings(
        C.STRATEGY,
        extra_active_windows=[C.window(s, e) for s, e in bo],
    )


def run(label, params, r, bo):
    s = bench(
        label,
        strategy_name=C.STRATEGY, symbol=C.SYMBOL, interval=C.TF,
        start=C.START, end=C.END,
        strategy_params=params,
        initial_equity=C.INITIAL_EQUITY,
        risk_per_trade=r,
        max_contracts=C.MAX_CONTRACTS,
        engine_settings=es_for(bo),
    )
    s["config"] = label.strip()
    return s


def main():
    print("=== 09 — RISK PUSH on (mf=31, ms=7) ===\n")
    results = []

    p = dict(C.V4_WINNER_PARAMS); p["mf_length"] = 31; p["mf_smooth"] = 7

    # BASE_A risk push
    print("[1] BASE_A mf=31 ms=7 — risk push:")
    for r in [0.0043, 0.0044, 0.0046, 0.0048, 0.0050, 0.0055, 0.006]:
        results.append(run(f"  BASE_A r={r}", p, r, BASE_A))

    # BASE_B risk push
    print("\n[2] BASE_B mf=31 ms=7 — risk push:")
    for r in [0.0043, 0.0044, 0.0046, 0.0048, 0.0050, 0.0055, 0.006]:
        results.append(run(f"  BASE_B r={r}", p, r, BASE_B))

    # Summary
    print("\n=== SUMMARY ===")
    for s in results:
        s["ratio"] = round(s["net_pnl"] / s["max_dd_$"], 2) if s["max_dd_$"] > 0 else 0
        s["under_2k"] = "✅" if s["max_dd_$"] < C.TARGET_MAX_DD else "❌"
        s["margin"] = round(C.TARGET_MAX_DD - s["max_dd_$"], 0)

    results.sort(key=lambda s: (-int(s["max_dd_$"] < C.TARGET_MAX_DD), -s["net_pnl"]))

    print(f"\n{'PASS':<5} {'PnL':>10} {'DD':>8} {'MARGIN':>8} {'RATIO':>6} {'N':>5} {'WR':>6} {'PF':>5} {'CONFIG':<25}")
    print("-" * 95)
    for s in results:
        print(f"{s['under_2k']:<5} ${s['net_pnl']:>8,.0f} "
              f"${s['max_dd_$']:>6,.0f} ${s['margin']:>6,.0f} {s['ratio']:>6.2f} "
              f"{s['trades']:>5} {s['win_rate']:>5.1f}% {s['profit_factor']:>5} {s['config']:<25}")

    safe = [s for s in results if s["max_dd_$"] < C.TARGET_MAX_DD and s["margin"] >= 100]
    safe.sort(key=lambda s: s["net_pnl"], reverse=True)
    print("\n=== SAFE PASSING (margin ≥ $100) by PnL ===")
    for s in safe:
        print(f"  PnL=${s['net_pnl']:>8,.0f} DD=${s['max_dd_$']:>6,.0f} "
              f"margin=${s['margin']:>5,.0f} ratio={s['ratio']:>6.2f} — {s['config']}")

    return results


if __name__ == "__main__":
    main()
