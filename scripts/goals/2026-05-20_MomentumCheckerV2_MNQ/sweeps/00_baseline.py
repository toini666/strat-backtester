"""Phase 0 — Confirm V1-compat anchor and benchmark V2 native defaults.

We do not need to re-replicate V1 (verify_momentum_checker_v2_vs_v1.py already
proved bit-identity). What we want here:
  1. Anchor: V2 with V1-compat translation on V1 engine ⇒ should print
     PnL=$61,313 / DD=$2,143 / N=785.
  2. V2 native defaults on the V1 engine — see how V2's new features behave
     out of the box.
  3. V2 native defaults on a minimal engine (only 22-23:59 active) — gives a
     baseline for the eventual blackout re-exploration in phase 8.
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
    ANCHOR_PARAMS,
    ANCHOR_PNL,
    ANCHOR_DD,
    END,
    INITIAL_EQUITY,
    INTERVAL,
    MAX_CONTRACTS,
    RISK_PER_TRADE,
    START,
    STRATEGY,
    SYMBOL,
    anchor_engine,
    minimal_engine,
)


def _common(engine):
    return dict(
        strategy_name=STRATEGY,
        symbol=SYMBOL,
        interval=INTERVAL,
        start=START,
        end=END,
        initial_equity=INITIAL_EQUITY,
        risk_per_trade=RISK_PER_TRADE,
        max_contracts=MAX_CONTRACTS,
        engine_settings=engine,
    )


def main() -> int:
    print("=" * 110)
    print(f"PHASE 0 — V2 baselines  |  {STRATEGY}  {SYMBOL} {INTERVAL}")
    print(f"period {START} → {END}  equity=${INITIAL_EQUITY:,.0f}  risk={RISK_PER_TRADE*100:.2f}%  max_ctr={MAX_CONTRACTS}")
    print(f"V1 anchor (target reproduction): PnL=${ANCHOR_PNL:,.0f}  DD=${ANCHOR_DD:,.0f}")
    print("=" * 110)
    print()

    t0 = time.time()
    n = 0

    s_anchor = bench(
        "[ANCHOR] V2 V1-compat / V1 engine",
        strategy_params=ANCHOR_PARAMS,
        **_common(anchor_engine()),
    )
    n += 1

    # V2 native defaults on V1 engine — empty override dict ⇒ use V2 defaults.
    s_v2def_v1eng = bench(
        "V2 defaults / V1 engine",
        strategy_params={},
        **_common(anchor_engine()),
    )
    n += 1

    # V2 native defaults on a minimal engine.
    s_v2def_min = bench(
        "V2 defaults / minimal engine (22-23:59)",
        strategy_params={},
        **_common(minimal_engine()),
    )
    n += 1

    # V1-compat anchor on minimal engine — shows what blackouts contribute.
    s_anchor_min = bench(
        "V2 V1-compat / minimal engine",
        strategy_params=ANCHOR_PARAMS,
        **_common(minimal_engine()),
    )
    n += 1

    elapsed = time.time() - t0
    print()
    print(f"Total: {n} sims in {elapsed:.0f}s ({elapsed/n:.1f}s/sim)")
    print()
    print("Anchor check:")
    print(f"  expected: PnL=${ANCHOR_PNL:,.0f} / DD=${ANCHOR_DD:,.0f}")
    print(f"  actual:   PnL=${s_anchor['net_pnl']:,.0f} / DD=${s_anchor['max_dd_$']:,.0f}")
    diff_pnl = abs(s_anchor['net_pnl'] - ANCHOR_PNL)
    diff_dd = abs(s_anchor['max_dd_$'] - ANCHOR_DD)
    if diff_pnl < 1.0 and diff_dd < 1.0:
        print("  ✅ MATCH")
    else:
        print(f"  ⚠ DRIFT: ΔPnL=${diff_pnl:.2f} ΔDD=${diff_dd:.2f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
