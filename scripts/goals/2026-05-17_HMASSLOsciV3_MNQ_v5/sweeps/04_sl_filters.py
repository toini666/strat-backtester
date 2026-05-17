"""04 — SL filter sweep on V5 base (V4 BO + H=08+12).

Tests intra-bar entry filters and SL caps on the new best blackout config:
  Base: V4 BO + H=08+12 → $50,089 / $1,962 / ratio 25.53.

Levers (1-D, then 2-D best combos):
  - max_candle_pct: 0.3, 0.4, 0.5, 0.7, 0.9 (current)
  - max_sl_points : 150, 200, 250, 300 (current)
  - cooldown_bars : 3 (current), 5, 7
  - tick_buffer   : 0 (current), 2, 4

Sort key: ratio + DD-under-2k. Looking for PnL ≥ V4 ($50,770) under DD<$2k.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _campaign as C  # noqa: E402

from scripts.goals._shared.harness import bench  # noqa: E402
from scripts.goals._shared.engine_settings import make_engine_settings  # noqa: E402


# V5 base blackouts (V4 BO + H=08+12)
V5_BO = [(11, 12), (14, 15), (8, 9), (12, 13)]


def es_base():
    return make_engine_settings(
        C.STRATEGY,
        extra_active_windows=[C.window(s, e) for s, e in V5_BO],
    )


def main():
    print("=== 04 — SL FILTERS on V5 base (V4 BO + H=08+12) ===\n")
    print("Base: $50,089 / $1,962 / ratio 25.53\n")
    results = []

    # (A) max_candle_pct sweep
    print("[A] max_candle_pct sweep (default 0.9):")
    for mcp in [0.3, 0.4, 0.5, 0.7, 0.9]:
        params = dict(C.V4_WINNER_PARAMS)
        params["max_candle_pct"] = mcp
        s = bench(
            f"  max_candle_pct={mcp}",
            strategy_name=C.STRATEGY, symbol=C.SYMBOL, interval=C.TF,
            start=C.START, end=C.END,
            strategy_params=params,
            initial_equity=C.INITIAL_EQUITY,
            risk_per_trade=C.DEFAULT_RISK,
            max_contracts=C.MAX_CONTRACTS,
            engine_settings=es_base(),
        )
        s["config"] = f"mcp={mcp}"
        results.append(s)

    # (B) max_sl_points sweep
    print("\n[B] max_sl_points sweep (default 300):")
    for sl in [150, 200, 250, 300]:
        params = dict(C.V4_WINNER_PARAMS)
        params["max_sl_points"] = float(sl)
        s = bench(
            f"  max_sl_points={sl}",
            strategy_name=C.STRATEGY, symbol=C.SYMBOL, interval=C.TF,
            start=C.START, end=C.END,
            strategy_params=params,
            initial_equity=C.INITIAL_EQUITY,
            risk_per_trade=C.DEFAULT_RISK,
            max_contracts=C.MAX_CONTRACTS,
            engine_settings=es_base(),
        )
        s["config"] = f"sl_pts={sl}"
        results.append(s)

    # (C) cooldown_bars sweep
    print("\n[C] cooldown_bars sweep (default 3):")
    for cb in [3, 5, 7]:
        params = dict(C.V4_WINNER_PARAMS)
        params["cooldown_bars"] = cb
        s = bench(
            f"  cooldown_bars={cb}",
            strategy_name=C.STRATEGY, symbol=C.SYMBOL, interval=C.TF,
            start=C.START, end=C.END,
            strategy_params=params,
            initial_equity=C.INITIAL_EQUITY,
            risk_per_trade=C.DEFAULT_RISK,
            max_contracts=C.MAX_CONTRACTS,
            engine_settings=es_base(),
        )
        s["config"] = f"cd={cb}"
        results.append(s)

    # (D) tick_buffer sweep
    print("\n[D] tick_buffer sweep (default 0):")
    for tb in [0, 2, 4]:
        params = dict(C.V4_WINNER_PARAMS)
        params["tick_buffer"] = tb
        s = bench(
            f"  tick_buffer={tb}",
            strategy_name=C.STRATEGY, symbol=C.SYMBOL, interval=C.TF,
            start=C.START, end=C.END,
            strategy_params=params,
            initial_equity=C.INITIAL_EQUITY,
            risk_per_trade=C.DEFAULT_RISK,
            max_contracts=C.MAX_CONTRACTS,
            engine_settings=es_base(),
        )
        s["config"] = f"tb={tb}"
        results.append(s)

    # (E) signal_candle_sl_on toggle
    print("\n[E] signal_candle_sl_on toggle (default False):")
    for v in [False, True]:
        params = dict(C.V4_WINNER_PARAMS)
        params["signal_candle_sl_on"] = v
        s = bench(
            f"  signal_candle_sl_on={v}",
            strategy_name=C.STRATEGY, symbol=C.SYMBOL, interval=C.TF,
            start=C.START, end=C.END,
            strategy_params=params,
            initial_equity=C.INITIAL_EQUITY,
            risk_per_trade=C.DEFAULT_RISK,
            max_contracts=C.MAX_CONTRACTS,
            engine_settings=es_base(),
        )
        s["config"] = f"sig_sl={v}"
        results.append(s)

    # Summary
    print("\n=== SUMMARY ===")
    for s in results:
        s["ratio"] = round(s["net_pnl"] / s["max_dd_$"], 2) if s["max_dd_$"] > 0 else 0
        s["under_2k"] = "✅" if s["max_dd_$"] < C.TARGET_MAX_DD else "❌"
    results.sort(key=lambda s: s["ratio"], reverse=True)

    print(f"\n{'PASS':<5} {'RATIO':>6} {'PnL':>10} {'DD':>8} {'N':>5} {'WR':>6} {'PF':>5} {'CONFIG':<25}")
    print("-" * 85)
    for s in results:
        print(f"{s['under_2k']:<5} {s['ratio']:>6.2f} ${s['net_pnl']:>8,.0f} "
              f"${s['max_dd_$']:>6,.0f} {s['trades']:>5} {s['win_rate']:>5.1f}% "
              f"{s['profit_factor']:>5} {s['config']:<25}")

    return results


if __name__ == "__main__":
    main()
