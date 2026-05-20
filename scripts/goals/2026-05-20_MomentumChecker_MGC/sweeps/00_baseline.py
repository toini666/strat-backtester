"""Phase 0 — Baseline.

Run MomentumChecker.default_params on MGC 7m with only the 22:00-23:59
blackout active. Establish the cold-start metric we must beat.
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


def main() -> int:
    print("=" * 100)
    print(f"PHASE 0 — Baseline  |  {STRATEGY}  {SYMBOL} {INTERVAL}")
    print(f"period {START} → {END}  equity=${INITIAL_EQUITY:,.0f}  risk={RISK_PER_TRADE*100:.2f}%  max_ctr={MAX_CONTRACTS}")
    print(f"engine: only 22:00-23:59 blackout active, no daily limits")
    print("=" * 100)
    print()

    t0 = time.time()
    s = bench(
        "Baseline (default params)",
        strategy_name=STRATEGY,
        symbol=SYMBOL,
        interval=INTERVAL,
        start=START,
        end=END,
        strategy_params=BASELINE_PARAMS,
        initial_equity=INITIAL_EQUITY,
        risk_per_trade=RISK_PER_TRADE,
        max_contracts=MAX_CONTRACTS,
        engine_settings=baseline_engine(),
    )
    print(f"\nElapsed: {time.time() - t0:.1f}s — per-sim budget gauge.")
    print(f"Goal: PnL > 0 and DD <= $2,500")
    print(f"  current PnL: ${s['net_pnl']:,.0f}")
    print(f"  current DD:  ${s['max_dd_$']:,.0f}  ({s['max_dd_%']:.1f}%)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
