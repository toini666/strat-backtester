"""Phase 0 — Baseline sanity.

Replay the saved preset's params + engine settings. Expected outcome reflects
the user-saved metrics: net total_return ≈ -15.45% (≈ -$7,727 net PnL),
40% drawdown, 3,220 trades, 35.9% win rate.

This is the starting point — anything the campaign reports later must beat this.
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
    print(f"PHASE 0 — Baseline sanity  |  {STRATEGY}  {SYMBOL} {INTERVAL}")
    print(f"period {START} → {END}  equity=${INITIAL_EQUITY:,.0f}  risk={RISK_PER_TRADE*100:.2f}%")
    print("=" * 100)
    print("Expected from saved preset: PnL ≈ -$7,727 (-15.45%), DD ≈ 40%, N ≈ 3,220, WR ≈ 35.9%")
    print()

    t0 = time.time()
    s = bench(
        "Baseline (saved preset)",
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
    print(f"\nElapsed: {time.time() - t0:.1f}s — use this as the per-sim budget gauge.")
    print(f"Distance to goal: need PnL > 0 and DD <= $2,500")
    print(f"  current PnL: ${s['net_pnl']:,.0f}")
    print(f"  current DD:  ${s['max_dd_$']:,.0f}  ({s['max_dd_%']:.1f}%)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
