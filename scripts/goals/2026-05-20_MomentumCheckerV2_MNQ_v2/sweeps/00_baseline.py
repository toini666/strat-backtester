"""Phase 0 (v2) — Confirm the new B-combo baseline with the patched simulator.

Expected (from Phase 11 re-rank of v1 campaign):
  PnL=$71,371 / $DD=$2,900 / %DD=4.43% / N=781 / WR=41.0% / PF=1.63
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

CAMPAIGN_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CAMPAIGN_DIR / "sweeps"))

from scripts.goals._shared.harness import bench  # noqa: E402

from _campaign import (  # noqa: E402
    BASELINE_PARAMS,
    BASELINE_PNL,
    BASELINE_DD,
    END,
    INITIAL_EQUITY,
    INTERVAL,
    MAX_CONTRACTS,
    RISK_PER_TRADE,
    START,
    STRATEGY,
    SYMBOL,
    V1_PNL,
    V1_DD,
    anchor_engine,
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
        engine_settings=anchor_engine(),
    )


def main() -> int:
    print("=" * 110)
    print(f"PHASE 0 (v2) — New baseline check  |  {STRATEGY}  {SYMBOL} {INTERVAL}")
    print(f"V1 anchor:   PnL=${V1_PNL:,.0f}  $DD=${V1_DD:,.0f}")
    print(f"Expected B:  PnL=${BASELINE_PNL:,.0f}  $DD=${BASELINE_DD:,.0f}")
    print("=" * 110)

    t0 = time.time()
    s = bench("[B baseline]", strategy_params=BASELINE_PARAMS, **_common())
    elapsed = time.time() - t0
    print(f"\nElapsed: {elapsed:.1f}s")
    print(f"Actual $DD: ${s['max_dd_$']:,.0f}  Expected: ${BASELINE_DD:,.0f}  Δ=${abs(s['max_dd_$']-BASELINE_DD):.0f}")
    print(f"Actual PnL: ${s['net_pnl']:,.0f}  Expected: ${BASELINE_PNL:,.0f}  Δ=${abs(s['net_pnl']-BASELINE_PNL):.0f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
