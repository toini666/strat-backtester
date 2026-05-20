"""Phase 0 — Establish the V2 V1-compat baseline on MGC.

V2 dropped Rob Reversal, which V1 MGC actively used (rob_on=True, pts_rob=1).
This means the V1-compat baseline on V2 cannot reproduce V1's entries — the
strategy will have fewer entries (or score-differently). We record actual
V2 numbers here so subsequent phases have a known starting point.

Also samples a few risk levels around 0.6% to see where the DD lands vs the
user's hard ceiling ($2,500) and soft target ($2,000).
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
    DD_CEILING,
    DD_TARGET,
    END,
    INITIAL_EQUITY,
    INTERVAL,
    MAX_CONTRACTS,
    RISK_PER_TRADE,
    START,
    STRATEGY,
    SYMBOL,
    V1_COMPAT_PARAMS,
    anchor_engine,
)


def _common(risk=RISK_PER_TRADE):
    return dict(
        strategy_name=STRATEGY,
        symbol=SYMBOL,
        interval=INTERVAL,
        start=START,
        end=END,
        initial_equity=INITIAL_EQUITY,
        risk_per_trade=risk,
        max_contracts=MAX_CONTRACTS,
        engine_settings=anchor_engine(),
    )


def main() -> int:
    print("=" * 110)
    print(f"PHASE 0 — V2 V1-compat baseline on MGC  |  {STRATEGY}  {SYMBOL} {INTERVAL}")
    print(f"User constraints: DD ceiling ${DD_CEILING:,.0f} (hard) / ${DD_TARGET:,.0f} (soft)")
    print(f"V1 MGC anchor (patched DD): PnL=$56,353  $DD=$3,708 — over user's ceiling")
    print("=" * 110)

    t0 = time.time()

    # Anchor risk (0.6%)
    bench("[V1-compat @ 0.6%]", strategy_params=V1_COMPAT_PARAMS, **_common(0.006))

    # Sweep a small risk band to see DD/PnL behavior
    for r in (0.0050, 0.0045, 0.0040, 0.0035, 0.0030):
        bench(f"[V1-compat @ {r*100:.2f}%]", strategy_params=V1_COMPAT_PARAMS,
              **_common(r))

    elapsed = time.time() - t0
    print(f"\nTotal sims: 6  |  Elapsed: {elapsed:.1f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
