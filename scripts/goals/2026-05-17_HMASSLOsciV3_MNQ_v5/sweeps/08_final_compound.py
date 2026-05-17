"""08 — Final compound sweep.

Sweep 07 surfaced two boosters:
  - mf_length=31 (1-D best, beats mf=30)
  - mf_smooth=7 (1-D best on BASE_B mf=30, beats default ms=6)

Compound test:
  (1) mf=31 × ms=7 on both BASE_A and BASE_B
  (2) Risk ladders on each
  (3) Pick the WINNER candidate with margin ≥ $150 and max PnL

Top-3 candidates from sweep 07 (margin > $150):
  - BASE_A mf=31 r=0.004      → $58,692 / $1,807 / $193 — best PnL/safe
  - BASE_B mf=30 r=0.0042     → $58,120 / $1,769 / $231 — safest of top
  - BASE_B mf=30 ms=7 r=0.004 → $57,066 / $1,740 / $260 — extra margin
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
    print("=== 08 — FINAL COMPOUND SWEEP ===\n")
    results = []

    # (1) mf=31 × ms=7 on BASE_A
    print("[1] BASE_A mf=31 × ms variants:")
    for ms in [6, 7, 8]:
        for r in [0.0038, 0.0040, 0.0042]:
            p = dict(C.V4_WINNER_PARAMS); p["mf_length"] = 31; p["mf_smooth"] = ms
            results.append(run(f"  BASE_A mf=31 ms={ms} r={r}", p, r, BASE_A))

    # (2) mf=31 × ms=7 on BASE_B
    print("\n[2] BASE_B mf=31 × ms variants:")
    for ms in [6, 7, 8]:
        for r in [0.0038, 0.0040, 0.0042]:
            p = dict(C.V4_WINNER_PARAMS); p["mf_length"] = 31; p["mf_smooth"] = ms
            results.append(run(f"  BASE_B mf=31 ms={ms} r={r}", p, r, BASE_B))

    # (3) mf=30 ms=7 on BASE_A
    print("\n[3] BASE_A mf=30 ms=7 risk ladder:")
    for r in [0.0038, 0.0040, 0.0042]:
        p = dict(C.V4_WINNER_PARAMS); p["mf_length"] = 30; p["mf_smooth"] = 7
        results.append(run(f"  BASE_A mf=30 ms=7 r={r}", p, r, BASE_A))

    # (4) Final stress: BASE_B mf=30 ms=7 risk ladder fine
    print("\n[4] BASE_B mf=30 ms=7 risk ladder fine:")
    for r in [0.0040, 0.0041, 0.0042, 0.0043]:
        p = dict(C.V4_WINNER_PARAMS); p["mf_length"] = 30; p["mf_smooth"] = 7
        results.append(run(f"  BASE_B mf=30 ms=7 r={r}", p, r, BASE_B))

    # Summary
    print("\n=== SUMMARY ===")
    for s in results:
        s["ratio"] = round(s["net_pnl"] / s["max_dd_$"], 2) if s["max_dd_$"] > 0 else 0
        s["under_2k"] = "✅" if s["max_dd_$"] < C.TARGET_MAX_DD else "❌"
        s["margin"] = round(C.TARGET_MAX_DD - s["max_dd_$"], 0)

    # Sort: passing first, then PnL desc
    results.sort(key=lambda s: (-int(s["max_dd_$"] < C.TARGET_MAX_DD), -s["net_pnl"]))

    print(f"\n{'PASS':<5} {'PnL':>10} {'DD':>8} {'MARGIN':>8} {'RATIO':>6} {'N':>5} {'WR':>6} {'PF':>5} {'CONFIG':<35}")
    print("-" * 105)
    for s in results:
        print(f"{s['under_2k']:<5} ${s['net_pnl']:>8,.0f} "
              f"${s['max_dd_$']:>6,.0f} ${s['margin']:>6,.0f} {s['ratio']:>6.2f} "
              f"{s['trades']:>5} {s['win_rate']:>5.1f}% {s['profit_factor']:>5} {s['config']:<35}")

    # WINNERS: passing with margin ≥ $150 (safe replay variance)
    safe = [s for s in results if s["max_dd_$"] < C.TARGET_MAX_DD and s["margin"] >= 150]
    safe.sort(key=lambda s: s["net_pnl"], reverse=True)
    print("\n=== SAFE PASSING (margin ≥ $150) by PnL ===")
    for s in safe[:10]:
        print(f"  PnL=${s['net_pnl']:>8,.0f} DD=${s['max_dd_$']:>6,.0f} "
              f"margin=${s['margin']:>5,.0f} ratio={s['ratio']:>6.2f} — {s['config']}")

    return results


if __name__ == "__main__":
    main()
