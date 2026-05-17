"""04 — Strategy params 1D sweep around new cloud=T mf=29 ms=5 base.

Sims used: ~50 / 200 → cumulative ~87/200
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from scripts.goals._shared.harness import bench  # noqa: E402
from scripts.goals._shared.engine_settings import make_engine_settings  # noqa: E402

from _campaign import (  # noqa: E402
    STRATEGY, SYMBOL, INTERVAL, START, END,
    INITIAL_EQUITY, MAX_CONTRACTS,
    V2_WINNER_OVERRIDES, V2_WINNER_RISK, V2_WINNER_BLACKOUTS,
    pdd,
)


CLOUD_BASE = dict(V2_WINNER_OVERRIDES)
CLOUD_BASE.update({"cloud_on": True, "mf_length": 29, "mf_smooth": 5})


def _es():
    return make_engine_settings(
        STRATEGY,
        extra_active_windows=[
            {"start_hour": sh, "start_minute": sm, "end_hour": eh, "end_minute": em}
            for (sh, sm, eh, em) in V2_WINNER_BLACKOUTS
        ],
    )


def _run(label, overrides, risk=V2_WINNER_RISK):
    p = dict(CLOUD_BASE)
    p.update(overrides)
    s = bench(
        label,
        strategy_name=STRATEGY, symbol=SYMBOL, interval=INTERVAL,
        start=START, end=END,
        strategy_params=p, initial_equity=INITIAL_EQUITY,
        risk_per_trade=risk, max_contracts=MAX_CONTRACTS,
        engine_settings=_es(),
    )
    return s


def sweep(label_prefix, key, values):
    print()
    print(f"--- 1D sweep: {key} ---")
    out = []
    for v in values:
        out.append(_run(f"{label_prefix} {key}={v}", {key: v}))
    return out


def main():
    print("=" * 80)
    print("Base: cloud=T mf=29 ms=5 + V2 overrides + V2 BO + r=0.47%")
    print("=" * 80)
    results = []
    results.append(_run("BASE", {}))

    # Indicator lengths
    results.extend(sweep("v", "ema_len", [9, 11, 13, 15]))
    results.extend(sweep("v", "hma1_len", [7, 8, 9, 10, 11]))
    results.extend(sweep("v", "hma2_len", [28, 30, 34, 38, 42]))
    results.extend(sweep("v", "ssl_len", [40, 60, 80, 100]))
    results.extend(sweep("v", "hyper_wave_length", [4, 5, 6, 7]))
    results.extend(sweep("v", "signal_length", [2, 3, 4, 5]))

    # Filters / exits
    results.extend(sweep("v", "max_sl_points", [60, 80, 100, 120, 150]))
    results.extend(sweep("v", "tick_buffer", [0, 1, 2]))
    results.extend(sweep("v", "cooldown_bars", [0, 1, 3, 5]))
    results.extend(sweep("v", "entry_window_bars", [3, 5, 7]))
    results.extend(sweep("v", "hma_pol_bars", [1, 2, 3, 4]))
    results.extend(sweep("v", "amp_mult", [1.5, 2.0, 2.5, 3.0]))

    # Extremes
    results.extend(sweep("v", "hw_extreme", [15, 18, 20, 22, 25]))
    results.extend(sweep("v", "sig_extreme", [30, 35, 40, 45]))

    # Exit
    results.extend(sweep("v", "final_exit_pct", [0.0, 0.1, 0.25, 0.5]))

    print()
    print("=" * 80)
    print("TOP 15 (by ratio, DD<2000)")
    print("=" * 80)
    safe = [r for r in results if r["max_dd_$"] < 2_000]
    safe.sort(key=lambda r: pdd(r["net_pnl"], r["max_dd_$"]), reverse=True)
    for r in safe[:15]:
        ratio = pdd(r["net_pnl"], r["max_dd_$"])
        print(f"  {r['label']:<45} PnL=${r['net_pnl']:>9,.0f} DD=${r['max_dd_$']:>6,.0f} P/DD={ratio:.2f}")

    print()
    print("=" * 80)
    print("TOP 10 by PnL (DD<2000)")
    print("=" * 80)
    safe2 = sorted(safe, key=lambda r: r["net_pnl"], reverse=True)
    for r in safe2[:10]:
        ratio = pdd(r["net_pnl"], r["max_dd_$"])
        print(f"  {r['label']:<45} PnL=${r['net_pnl']:>9,.0f} DD=${r['max_dd_$']:>6,.0f} P/DD={ratio:.2f}")


if __name__ == "__main__":
    main()
