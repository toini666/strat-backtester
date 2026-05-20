"""Phase 2 — Risk geometry on top of min_gap=9.

Phase 1 winner = min_gap=9 (PnL=$11,381, DD=$6,846, P/DD=1.66, N=1009).
Goal: see if rr_tp, sl_lookback, sl_max_points, tick_buffer can push P/DD higher.
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


PHASE1_WINNER = dict(BASELINE_PARAMS)
PHASE1_WINNER["min_gap"] = 9


SWEEPS = {
    "rr_tp":          [1.5, 1.75, 2.0, 2.25, 2.5, 2.75, 3.0, 3.5, 4.0],
    "sl_lookback":    [2, 3, 4, 5, 7, 10, 15, 20],
    "sl_max_points":  [30.0, 50.0, 75.0, 100.0, 150.0, 200.0, 300.0],
    "tick_buffer":    [0, 1, 2, 3, 5, 8],
    "max_candle_pct": [0.2, 0.3, 0.4, 0.6, 0.8],
}


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


def _override(**kwargs):
    p = dict(PHASE1_WINNER)
    p.update(kwargs)
    return p


def main() -> int:
    print("=" * 100)
    print(f"PHASE 2 — Risk geometry  |  baseline = min_gap=9 winner")
    print("=" * 100)

    t0 = time.time()
    n = 0
    all_results = []

    base = bench("Phase-1 winner (min_gap=9)", strategy_params=PHASE1_WINNER, **_common())
    n += 1
    all_results.append(("(=base) min_gap=9", base))

    for param, values in SWEEPS.items():
        baseline_val = PHASE1_WINNER.get(param)
        print()
        print("-" * 100)
        print(f"SWEEP {param}  (winner baseline = {baseline_val})")
        for v in values:
            mark = " (=base)" if v == baseline_val else ""
            label = f"{param}={v}{mark}"
            s = bench(label, strategy_params=_override(**{param: v}), **_common())
            n += 1
            all_results.append((label, s))

    elapsed = time.time() - t0
    print()
    print(f"Total: {n} sims in {elapsed:.0f}s")

    print()
    print("=" * 100)
    print("DD-VALID (≤$2,500) results sorted by PnL")
    print("=" * 100)
    dd_valid = [(l, s) for l, s in all_results if s["max_dd_$"] <= 2500]
    for l, s in sorted(dd_valid, key=lambda x: -x[1]["net_pnl"])[:15]:
        print(f"  PnL=${s['net_pnl']:>7,.0f}  DD=${s['max_dd_$']:>5,.0f}  N={s['trades']:>4}  WR={s['win_rate']:.1f}%  ← {l}")
    if not dd_valid:
        print("  (none)")

    print()
    print("=" * 100)
    print("Top 10 by P/DD ratio (any DD)")
    print("=" * 100)
    for l, s in sorted(all_results, key=lambda x: -x[1]["net_pnl"] / max(x[1]["max_dd_$"], 1.0))[:10]:
        p_dd = s["net_pnl"] / max(s["max_dd_$"], 1.0)
        print(f"  P/DD={p_dd:>5.2f}  PnL=${s['net_pnl']:>7,.0f}  DD=${s['max_dd_$']:>6,.0f}  N={s['trades']:>4}  WR={s['win_rate']:.1f}%  ← {l}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
