"""Phase 0b — Selectivity probe.

Diagnosis: baseline has 3,220 trades / 35.9% WR / PF 0.98 / AW $366 vs AL -$209.
The trade geometry is fine; the problem is "too many low-quality entries".

Probe: tighten thresholds and re-measure. If none of these gets near positive
PnL we will know parameter tuning alone won't reach the goal.

Also reads the per-sim runtime on warm cache (baseline first triggered the data
load; from now on `bench` should be quick).
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
    p = dict(BASELINE_PARAMS)
    p.update(kwargs)
    return p


def main() -> int:
    print("=" * 100)
    print("PHASE 0b — Selectivity probe (5 sims)")
    print("=" * 100)
    print("Hypothesis: baseline = too many entries. Tightening should improve PF and WR.")
    print()

    t0 = time.time()
    sims = []
    sims.append(bench("Baseline (warm-cache)",                 strategy_params=BASELINE_PARAMS, **_common()))
    sims.append(bench("LT=6 ST=6 gap=4",                       strategy_params=_override(long_threshold=6, short_threshold=6, min_gap=4), **_common()))
    sims.append(bench("LT=7 ST=7 gap=5",                       strategy_params=_override(long_threshold=7, short_threshold=7, min_gap=5), **_common()))
    sims.append(bench("LT=8 ST=8 gap=6",                       strategy_params=_override(long_threshold=8, short_threshold=8, min_gap=6), **_common()))
    sims.append(bench("LT=10 ST=10 gap=6",                     strategy_params=_override(long_threshold=10, short_threshold=10, min_gap=6), **_common()))
    sims.append(bench("LT=7 ST=7 gap=5 candle=0.2",            strategy_params=_override(long_threshold=7, short_threshold=7, min_gap=5, max_candle_pct=0.2), **_common()))
    elapsed = time.time() - t0
    print(f"\nTotal: {len(sims)} sims in {elapsed:.1f}s — ~{elapsed/len(sims):.1f}s/sim (warm cache)")
    print()
    print("Verdict:")
    valid = [s for s in sims if s["max_dd_$"] <= 2500]
    if any(s["net_pnl"] > 0 for s in sims):
        best = max(sims, key=lambda s: s["net_pnl"])
        print(f"  Best PnL among probe: {best['label']} → PnL=${best['net_pnl']:,.0f}, DD=${best['max_dd_$']:,.0f}")
    if valid and any(s["net_pnl"] > 0 for s in valid):
        best_valid = max([s for s in valid if s["net_pnl"] > 0], key=lambda s: s["net_pnl"])
        print(f"  Best DD-valid (≤$2.5k) probe: {best_valid['label']} → PnL=${best_valid['net_pnl']:,.0f}, DD=${best_valid['max_dd_$']:,.0f}")
        print("  → strategy looks salvageable; proceed with Phase 2 (thresholds/gap fine sweep).")
    else:
        print("  No probe achieved positive PnL with DD≤$2.5k. Strategy may need deeper rework.")
        print("  Continue cautiously — possibly need to disable modules first.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
