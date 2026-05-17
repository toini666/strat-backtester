"""06 — mf_length finetune + risk ladder + cross-combos.

Sweep 05 breakthrough: mf_length is non-monotone with sweet spots at 20 and 30,
valley at 25 (V4 default). Both 20 and 30 pass DD<$2k AT V4 RISK (r=0.0036).

Levers to combine:
  (1) mf_length fine grid [17, 18, 19, 20, 21, 22, 28, 29, 30, 31, 32]
  (2) Risk ladder on each mf candidate
  (3) mf × sig_extreme combo (sx=45 had +PnL but failed DD — could combine?)
  (4) mf × ema_len combo
  (5) BASE_B (extra +H=04) with mf=20/30 (safer)
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
    print("=== 06 — mf FINETUNE + RISK + COMBOS ===\n")
    results = []

    # (1) mf_length fine grid on BASE_A at V4 risk
    print("[1] mf_length fine grid on BASE_A r=0.0036:")
    for mfl in [17, 18, 19, 20, 21, 22, 28, 29, 30, 31, 32]:
        p = dict(C.V4_WINNER_PARAMS); p["mf_length"] = mfl
        results.append(run(f"  BASE_A mf={mfl}", p, 0.0036, BASE_A))

    # (2) Risk ladder on mf=30 (best ratio in sweep 05)
    print("\n[2] Risk ladder on BASE_A mf=30:")
    for r in [0.0034, 0.0036, 0.0037, 0.0038, 0.0040]:
        p = dict(C.V4_WINNER_PARAMS); p["mf_length"] = 30
        results.append(run(f"  BASE_A mf=30 r={r}", p, r, BASE_A))

    # (3) Risk ladder on mf=20 (best PnL in sweep 05)
    print("\n[3] Risk ladder on BASE_A mf=20:")
    for r in [0.0034, 0.0036, 0.0037, 0.0038, 0.0040]:
        p = dict(C.V4_WINNER_PARAMS); p["mf_length"] = 20
        results.append(run(f"  BASE_A mf=20 r={r}", p, r, BASE_A))

    # (4) BASE_B (safer) with mf candidates
    print("\n[4] BASE_B (+H=04) with mf=20/30:")
    for mfl in [20, 25, 30]:
        for r in [0.0036, 0.0038, 0.0040]:
            p = dict(C.V4_WINNER_PARAMS); p["mf_length"] = mfl
            results.append(run(f"  BASE_B mf={mfl} r={r}", p, r, BASE_B))

    # (5) mf=30 × sx=45 (compound winners from sweep 05)
    print("\n[5] BASE_A mf=30 × sig_extreme:")
    for sx in [35, 40, 45]:
        p = dict(C.V4_WINNER_PARAMS); p["mf_length"] = 30; p["sig_extreme"] = sx
        results.append(run(f"  BASE_A mf=30 sx={sx}", p, 0.0036, BASE_A))

    # (6) mf=20 × sx
    print("\n[6] BASE_A mf=20 × sig_extreme:")
    for sx in [35, 40, 45]:
        p = dict(C.V4_WINNER_PARAMS); p["mf_length"] = 20; p["sig_extreme"] = sx
        results.append(run(f"  BASE_A mf=20 sx={sx}", p, 0.0036, BASE_A))

    # Summary
    print("\n=== SUMMARY ===")
    for s in results:
        s["ratio"] = round(s["net_pnl"] / s["max_dd_$"], 2) if s["max_dd_$"] > 0 else 0
        s["under_2k"] = "✅" if s["max_dd_$"] < C.TARGET_MAX_DD else "❌"

    # Sort by passing-status then PnL (desc)
    results.sort(key=lambda s: (-int(s["max_dd_$"] < C.TARGET_MAX_DD), -s["net_pnl"]))

    print(f"\n{'PASS':<5} {'PnL':>10} {'DD':>8} {'MARGIN':>8} {'RATIO':>6} {'N':>5} {'WR':>6} {'PF':>5} {'CONFIG':<30}")
    print("-" * 100)
    for s in results:
        margin = C.TARGET_MAX_DD - s["max_dd_$"]
        print(f"{s['under_2k']:<5} ${s['net_pnl']:>8,.0f} "
              f"${s['max_dd_$']:>6,.0f} ${margin:>6,.0f} {s['ratio']:>6.2f} "
              f"{s['trades']:>5} {s['win_rate']:>5.1f}% {s['profit_factor']:>5} {s['config']:<30}")

    # Top 10 passing
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
