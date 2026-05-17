"""07 — Micro-finetune around the top candidate.

Sweep 06 winner: BASE_B + mf=30 + r=0.0040 → $55,766 / $1,660 / margin $340.

Tasks here:
  (1) Push r higher on BASE_B mf=30 to find the DD-wall.
  (2) Test mf=29/31 around r=0.004 to confirm mf=30 is a local optimum.
  (3) Test sx variants on the winner.
  (4) Confirm final_exit_pct doesn't help.
  (5) Verify BASE_A best candidates still pass at higher risk.
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
    print("=== 07 — MICRO-FINETUNE AROUND TOP CANDIDATE ===\n")
    results = []

    # (1) Push r on BASE_B mf=30
    print("[1] Push r on BASE_B mf=30:")
    for r in [0.0040, 0.0042, 0.0044, 0.0045, 0.0046, 0.0048, 0.0050]:
        p = dict(C.V4_WINNER_PARAMS); p["mf_length"] = 30
        results.append(run(f"  BASE_B mf=30 r={r}", p, r, BASE_B))

    # (2) mf neighbors around 30 on BASE_B
    print("\n[2] mf neighbors on BASE_B r=0.0040:")
    for mfl in [28, 29, 30, 31, 32]:
        p = dict(C.V4_WINNER_PARAMS); p["mf_length"] = mfl
        results.append(run(f"  BASE_B mf={mfl} r=0.004", p, 0.0040, BASE_B))

    # (3) sx variants on BASE_B mf=30 r=0.004 (best)
    print("\n[3] sx variants on BASE_B mf=30 r=0.004:")
    for sx in [35, 40, 45]:
        p = dict(C.V4_WINNER_PARAMS); p["mf_length"] = 30; p["sig_extreme"] = sx
        results.append(run(f"  BASE_B mf=30 sx={sx} r=0.004", p, 0.0040, BASE_B))

    # (4) Push BASE_A mf=30 + sx=35 (had margin $410)
    print("\n[4] BASE_A mf=30 sx=35 risk ladder:")
    for r in [0.0036, 0.0038, 0.0040, 0.0042]:
        p = dict(C.V4_WINNER_PARAMS); p["mf_length"] = 30; p["sig_extreme"] = 35
        results.append(run(f"  BASE_A mf=30 sx=35 r={r}", p, r, BASE_A))

    # (5) BASE_A mf=31 risk ladder
    print("\n[5] BASE_A mf=31 risk ladder:")
    for r in [0.0036, 0.0038, 0.0040, 0.0042]:
        p = dict(C.V4_WINNER_PARAMS); p["mf_length"] = 31
        results.append(run(f"  BASE_A mf=31 r={r}", p, r, BASE_A))

    # (6) mf_smooth probe (V4 default 6)
    print("\n[6] mf_smooth probe on BASE_B mf=30 r=0.004:")
    for ms in [4, 5, 6, 7, 8]:
        p = dict(C.V4_WINNER_PARAMS); p["mf_length"] = 30; p["mf_smooth"] = ms
        results.append(run(f"  BASE_B mf=30 ms={ms}", p, 0.0040, BASE_B))

    # Summary
    print("\n=== SUMMARY ===")
    for s in results:
        s["ratio"] = round(s["net_pnl"] / s["max_dd_$"], 2) if s["max_dd_$"] > 0 else 0
        s["under_2k"] = "✅" if s["max_dd_$"] < C.TARGET_MAX_DD else "❌"

    results.sort(key=lambda s: (-int(s["max_dd_$"] < C.TARGET_MAX_DD), -s["net_pnl"]))

    print(f"\n{'PASS':<5} {'PnL':>10} {'DD':>8} {'MARGIN':>8} {'RATIO':>6} {'N':>5} {'WR':>6} {'PF':>5} {'CONFIG':<30}")
    print("-" * 100)
    for s in results:
        margin = C.TARGET_MAX_DD - s["max_dd_$"]
        print(f"{s['under_2k']:<5} ${s['net_pnl']:>8,.0f} "
              f"${s['max_dd_$']:>6,.0f} ${margin:>6,.0f} {s['ratio']:>6.2f} "
              f"{s['trades']:>5} {s['win_rate']:>5.1f}% {s['profit_factor']:>5} {s['config']:<30}")

    passing = [s for s in results if s["max_dd_$"] < C.TARGET_MAX_DD]
    passing.sort(key=lambda s: s["net_pnl"], reverse=True)
    print("\n=== TOP 10 PASSING by PnL ===")
    for s in passing[:10]:
        margin = C.TARGET_MAX_DD - s["max_dd_$"]
        print(f"  PnL=${s['net_pnl']:>8,.0f} DD=${s['max_dd_$']:>6,.0f} "
              f"margin=${margin:>5,.0f} ratio={s['ratio']:>6.2f} — {s['config']}")
    return results


if __name__ == "__main__":
    main()
