"""02 — Daily limits (intra_bar + after_close) + risk-scaling floor case.

Tests two orthogonal levers:
  (A) Risk floor — pure r scaling: r=0.0031 should give DD ≈ $1,950, PnL ≈ $43.7k.
      Establishes the GUARANTEED-success fallback. Any other config must beat
      this PnL under DD<$2,000.
  (B) Daily limits — V4 never tested these. Cap daily PnL with both intra_bar
      (close immediately on float) and after_close (close at next bar after
      close hits limit). Tight caps (~$300-700) at V4 risk to see if DD can be
      capped without killing the edge.

Sort key: Profit/DD ratio. Must clear 22.4 to be structurally better than
risk-scaled V4.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _campaign as C  # noqa: E402

from scripts.goals._shared.harness import bench  # noqa: E402
from scripts.goals._shared.engine_settings import make_engine_settings  # noqa: E402


V4_BLACKOUTS = [C.window(11, 12), C.window(14, 15)]


def es_base(daily_loss=None, daily_win=None, daily_mode="after_close"):
    return make_engine_settings(
        C.STRATEGY,
        extra_active_windows=V4_BLACKOUTS,
        daily_loss_limit=daily_loss,
        daily_win_limit=daily_win,
        daily_limit_mode=daily_mode,
    )


def main():
    print("=== 02 — DAILY LIMITS + RISK FLOOR ===\n")
    print(f"{'CONFIG':<55} RESULT")
    print("-" * 130)
    results = []

    # (A) Risk floor verification — pure scaling
    print("\n[A] Risk scaling floor (no daily limits, V4 BO):")
    for r in [0.0028, 0.0031, 0.0034]:
        s = bench(
            f"  r={r:.4f}  (NO daily limit)",
            strategy_name=C.STRATEGY, symbol=C.SYMBOL, interval=C.TF,
            start=C.START, end=C.END,
            strategy_params=dict(C.V4_WINNER_PARAMS),
            initial_equity=C.INITIAL_EQUITY,
            risk_per_trade=r,
            max_contracts=C.MAX_CONTRACTS,
            engine_settings=es_base(),
        )
        s["config"] = f"floor r={r}"
        results.append(s)

    # (B) Daily loss limit — intra_bar (the high-leverage untested mode)
    print("\n[B] Daily LOSS limit — intra_bar mode (V4 risk r=0.0036):")
    for loss in [300, 400, 500, 600, 700, 1000]:
        s = bench(
            f"  loss=${loss} intra_bar",
            strategy_name=C.STRATEGY, symbol=C.SYMBOL, interval=C.TF,
            start=C.START, end=C.END,
            strategy_params=dict(C.V4_WINNER_PARAMS),
            initial_equity=C.INITIAL_EQUITY,
            risk_per_trade=C.DEFAULT_RISK,
            max_contracts=C.MAX_CONTRACTS,
            engine_settings=es_base(daily_loss=loss, daily_mode="intra_bar"),
        )
        s["config"] = f"loss=${loss} intra"
        results.append(s)

    # (C) Daily loss limit — after_close (fallback mode)
    print("\n[C] Daily LOSS limit — after_close mode (V4 risk r=0.0036):")
    for loss in [400, 500, 700]:
        s = bench(
            f"  loss=${loss} after_close",
            strategy_name=C.STRATEGY, symbol=C.SYMBOL, interval=C.TF,
            start=C.START, end=C.END,
            strategy_params=dict(C.V4_WINNER_PARAMS),
            initial_equity=C.INITIAL_EQUITY,
            risk_per_trade=C.DEFAULT_RISK,
            max_contracts=C.MAX_CONTRACTS,
            engine_settings=es_base(daily_loss=loss, daily_mode="after_close"),
        )
        s["config"] = f"loss=${loss} after"
        results.append(s)

    # (D) Loss + win combined intra_bar — cap both ends
    print("\n[D] Daily LOSS + WIN limits — intra_bar (V4 risk r=0.0036):")
    for loss, win in [(400, 600), (500, 800), (700, 1000)]:
        s = bench(
            f"  loss=${loss} win=${win} intra_bar",
            strategy_name=C.STRATEGY, symbol=C.SYMBOL, interval=C.TF,
            start=C.START, end=C.END,
            strategy_params=dict(C.V4_WINNER_PARAMS),
            initial_equity=C.INITIAL_EQUITY,
            risk_per_trade=C.DEFAULT_RISK,
            max_contracts=C.MAX_CONTRACTS,
            engine_settings=es_base(daily_loss=loss, daily_win=win,
                                    daily_mode="intra_bar"),
        )
        s["config"] = f"loss=${loss} win=${win} intra"
        results.append(s)

    # Summary — sort by Profit/DD ratio, filter passing DD cap
    print("\n=== SUMMARY (sorted by Profit/DD ratio) ===")
    for s in results:
        s["ratio"] = round(s["net_pnl"] / s["max_dd_$"], 2) if s["max_dd_$"] > 0 else 0
        s["under_2k"] = "✅" if s["max_dd_$"] < C.TARGET_MAX_DD else "❌"
    results.sort(key=lambda s: s["ratio"], reverse=True)

    print(f"\n{'PASS':<5} {'RATIO':>6} {'PnL':>10} {'DD':>8} {'N':>5} {'WR':>6} {'PF':>5} {'CONFIG':<35}")
    print("-" * 95)
    for s in results:
        print(f"{s['under_2k']:<5} {s['ratio']:>6.2f} ${s['net_pnl']:>8,.0f} "
              f"${s['max_dd_$']:>6,.0f} {s['trades']:>5} {s['win_rate']:>5.1f}% "
              f"{s['profit_factor']:>5} {s['config']:<35}")

    print("\nTarget: ratio > 22.39 (V4 baseline ratio) AND DD < $2,000")
    qualifying = [s for s in results if s["max_dd_$"] < C.TARGET_MAX_DD]
    if qualifying:
        qualifying.sort(key=lambda s: s["net_pnl"], reverse=True)
        print(f"\nBest PnL under DD cap: ${qualifying[0]['net_pnl']:,.0f} "
              f"(DD ${qualifying[0]['max_dd_$']:,.0f}) — {qualifying[0]['config']}")
    return results


if __name__ == "__main__":
    main()
