"""05 — Risk sweep + small strategy variants on top blackout configs.

Top 2 from sweep 03:
  A) V4 BO + H=08+12      → $50,089 / $1,962 (ratio 25.53, margin $38)
  B) V4 BO + H=08+12+04   → $49,131 / $1,891 (ratio 25.99, margin $109)

V4 SL filters are locked-in (sweep 04). Test:
  (1) Risk ladder on both bases at r ∈ [0.0032, 0.0040] step 0.0002.
  (2) Small ema_len neighbors on best base (10, 11, 12).
  (3) Single-param probes (amp_mult, hma_pol_bars) on best base.

Goal: find a config with DD<$2,000 AND PnL > $50,089.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _campaign as C  # noqa: E402

from scripts.goals._shared.harness import bench  # noqa: E402
from scripts.goals._shared.engine_settings import make_engine_settings  # noqa: E402


BASE_A = [(11, 12), (14, 15), (8, 9), (12, 13)]           # +H=08+12
BASE_B = [(11, 12), (14, 15), (8, 9), (12, 13), (4, 5)]   # +H=08+12+04


def es_for(bo):
    return make_engine_settings(
        C.STRATEGY,
        extra_active_windows=[C.window(s, e) for s, e in bo],
    )


def main():
    print("=== 05 — RISK + STRATEGY MICRO-COMBOS ===\n")
    results = []

    # (1A) Risk sweep on BASE_A (V4 BO + H=08+12)
    print("[1A] Risk sweep on BASE_A (V4 BO + H=08+12):")
    for r in [0.0032, 0.0034, 0.0035, 0.0036, 0.0037, 0.0038, 0.0040]:
        s = bench(
            f"  BASE_A r={r}",
            strategy_name=C.STRATEGY, symbol=C.SYMBOL, interval=C.TF,
            start=C.START, end=C.END,
            strategy_params=dict(C.V4_WINNER_PARAMS),
            initial_equity=C.INITIAL_EQUITY,
            risk_per_trade=r,
            max_contracts=C.MAX_CONTRACTS,
            engine_settings=es_for(BASE_A),
        )
        s["config"] = f"BASE_A r={r}"
        results.append(s)

    # (1B) Risk sweep on BASE_B (V4 BO + H=08+12+04)
    print("\n[1B] Risk sweep on BASE_B (V4 BO + H=08+12+04):")
    for r in [0.0032, 0.0034, 0.0035, 0.0036, 0.0037, 0.0038, 0.0040]:
        s = bench(
            f"  BASE_B r={r}",
            strategy_name=C.STRATEGY, symbol=C.SYMBOL, interval=C.TF,
            start=C.START, end=C.END,
            strategy_params=dict(C.V4_WINNER_PARAMS),
            initial_equity=C.INITIAL_EQUITY,
            risk_per_trade=r,
            max_contracts=C.MAX_CONTRACTS,
            engine_settings=es_for(BASE_B),
        )
        s["config"] = f"BASE_B r={r}"
        results.append(s)

    # (2) ema_len neighbors on BASE_A
    print("\n[2] ema_len neighbors on BASE_A:")
    for ema in [10, 11, 12]:
        params = dict(C.V4_WINNER_PARAMS)
        params["ema_len"] = ema
        s = bench(
            f"  BASE_A ema={ema}",
            strategy_name=C.STRATEGY, symbol=C.SYMBOL, interval=C.TF,
            start=C.START, end=C.END,
            strategy_params=params,
            initial_equity=C.INITIAL_EQUITY,
            risk_per_trade=C.DEFAULT_RISK,
            max_contracts=C.MAX_CONTRACTS,
            engine_settings=es_for(BASE_A),
        )
        s["config"] = f"BASE_A ema={ema}"
        results.append(s)

    # (3) entry_window_bars sweep on BASE_A
    print("\n[3] entry_window_bars on BASE_A:")
    for ewb in [2, 3, 4, 5]:
        params = dict(C.V4_WINNER_PARAMS)
        params["entry_window_bars"] = ewb
        s = bench(
            f"  BASE_A ewb={ewb}",
            strategy_name=C.STRATEGY, symbol=C.SYMBOL, interval=C.TF,
            start=C.START, end=C.END,
            strategy_params=params,
            initial_equity=C.INITIAL_EQUITY,
            risk_per_trade=C.DEFAULT_RISK,
            max_contracts=C.MAX_CONTRACTS,
            engine_settings=es_for(BASE_A),
        )
        s["config"] = f"BASE_A ewb={ewb}"
        results.append(s)

    # (4) mf_length sweep on BASE_A
    print("\n[4] mf_length on BASE_A:")
    for mfl in [20, 25, 30, 35]:
        params = dict(C.V4_WINNER_PARAMS)
        params["mf_length"] = mfl
        s = bench(
            f"  BASE_A mf={mfl}",
            strategy_name=C.STRATEGY, symbol=C.SYMBOL, interval=C.TF,
            start=C.START, end=C.END,
            strategy_params=params,
            initial_equity=C.INITIAL_EQUITY,
            risk_per_trade=C.DEFAULT_RISK,
            max_contracts=C.MAX_CONTRACTS,
            engine_settings=es_for(BASE_A),
        )
        s["config"] = f"BASE_A mf={mfl}"
        results.append(s)

    # (5) sig_extreme on BASE_A
    print("\n[5] sig_extreme on BASE_A:")
    for sx in [30, 35, 40, 45]:
        params = dict(C.V4_WINNER_PARAMS)
        params["sig_extreme"] = sx
        s = bench(
            f"  BASE_A sx={sx}",
            strategy_name=C.STRATEGY, symbol=C.SYMBOL, interval=C.TF,
            start=C.START, end=C.END,
            strategy_params=params,
            initial_equity=C.INITIAL_EQUITY,
            risk_per_trade=C.DEFAULT_RISK,
            max_contracts=C.MAX_CONTRACTS,
            engine_settings=es_for(BASE_A),
        )
        s["config"] = f"BASE_A sx={sx}"
        results.append(s)

    # Summary
    print("\n=== SUMMARY ===")
    for s in results:
        s["ratio"] = round(s["net_pnl"] / s["max_dd_$"], 2) if s["max_dd_$"] > 0 else 0
        s["under_2k"] = "✅" if s["max_dd_$"] < C.TARGET_MAX_DD else "❌"
    results.sort(key=lambda s: s["ratio"], reverse=True)

    print(f"\n{'PASS':<5} {'RATIO':>6} {'PnL':>10} {'DD':>8} {'N':>5} {'WR':>6} {'PF':>5} {'CONFIG':<30}")
    print("-" * 90)
    for s in results:
        print(f"{s['under_2k']:<5} {s['ratio']:>6.2f} ${s['net_pnl']:>8,.0f} "
              f"${s['max_dd_$']:>6,.0f} {s['trades']:>5} {s['win_rate']:>5.1f}% "
              f"{s['profit_factor']:>5} {s['config']:<30}")

    print("\n=== PASSING (DD<$2k) — by PnL ===")
    passing = [s for s in results if s["max_dd_$"] < C.TARGET_MAX_DD]
    passing.sort(key=lambda s: s["net_pnl"], reverse=True)
    for s in passing[:10]:
        print(f"  PnL=${s['net_pnl']:>8,.0f} DD=${s['max_dd_$']:>6,.0f} "
              f"margin=${C.TARGET_MAX_DD - s['max_dd_$']:>5,.0f} "
              f"ratio={s['ratio']:>6.2f} — {s['config']}")
    return results


if __name__ == "__main__":
    main()
