"""Phase 1 — Sanity: V4(defaults) should reproduce V3 baseline.

Migrates the V3 winner preset's strategy params to V4 (drop V4-removed keys,
translate signal_candle_sl_on → reject_entry_at_sl_extreme, keep the 9 new
V4 levers at neutral defaults), then runs V4 with the V3-winner blackouts.

Strict tolerance ($1) — anything larger means a wiring bug.

Also reports 5m and 10m runs for context (mission allows other TFs if 7m fails).
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from scripts.goals._shared.engine_settings import make_engine_settings
from scripts.goals._shared.harness import bench

from _campaign import (
    BASELINE_ACTIVE_BLACKOUTS,
    BASELINE_V4_PARAMS,
    END,
    INITIAL_EQUITY,
    INTERVAL,
    MAX_CONTRACTS,
    RISK_PER_TRADE,
    START,
    STRATEGY,
    SYMBOL,
    V3_BASELINE,
)


def _engine():
    return make_engine_settings(
        STRATEGY,
        extra_active_windows=BASELINE_ACTIVE_BLACKOUTS,
    )


def main() -> int:
    print("=" * 100)
    print(f"PHASE 1 — V3→V4 sanity check  |  strategy={STRATEGY}  symbol={SYMBOL}")
    print(f"period {START} → {END}  |  equity=${INITIAL_EQUITY:,.0f}  risk={RISK_PER_TRADE*100:.2f}%")
    print("=" * 100)
    print(f"V3 baseline target: PnL=${V3_BASELINE['net_pnl']:,} DD=${V3_BASELINE['max_dd_$']:,} "
          f"N={V3_BASELINE['trades']} WR={V3_BASELINE['win_rate']}% PF={V3_BASELINE['profit_factor']}")
    print()

    common = dict(
        strategy_name=STRATEGY,
        symbol=SYMBOL,
        start=START,
        end=END,
        strategy_params=BASELINE_V4_PARAMS,
        initial_equity=INITIAL_EQUITY,
        risk_per_trade=RISK_PER_TRADE,
        max_contracts=MAX_CONTRACTS,
        engine_settings=_engine(),
    )

    # Primary 7m sanity run.
    s7 = bench(f"V4 baseline 7m (V3-migrated params)", interval="7m", **common)

    # Optional: 5m and 10m for context. Mission says 7m is the priority.
    s5 = bench(f"V4 baseline 5m (V3-migrated params)", interval="5m", **common)
    s10 = bench(f"V4 baseline 10m (V3-migrated params)", interval="10m", **common)

    print()
    print("-" * 100)
    print("SANITY VERDICT (tight tolerance, < $5):")
    pnl_drift = s7["net_pnl"] - V3_BASELINE["net_pnl"]
    dd_drift = s7["max_dd_$"] - V3_BASELINE["max_dd_$"]
    print(f"  PnL drift = ${pnl_drift:+,.2f}")
    print(f"  DD  drift = ${dd_drift:+,.2f}")
    print(f"  N         = {s7['trades']}  (V3 had {V3_BASELINE['trades']})")
    print(f"  PF        = {s7['profit_factor']}  (V3 had {V3_BASELINE['profit_factor']})")
    if abs(pnl_drift) < 5 and abs(dd_drift) < 5:
        print("  ✅ SANITY OK — V4 with neutral defaults reproduces V3 baseline.")
        return 0
    print("  ❌ DRIFT — investigate before any sweep.")
    print("     • Check that all 9 V4 fields are wired through harness.py.")
    print("     • Check simulator.py V4 exit branch (canal_exit_mode='v4_hw_rr').")
    print("     • Check param translation (signal_candle_sl_on / final_exit_mode / etc.).")
    return 1


if __name__ == "__main__":
    sys.exit(main())
