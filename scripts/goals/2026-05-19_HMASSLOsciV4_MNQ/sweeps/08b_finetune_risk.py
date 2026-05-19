"""Phase 8b — Fine-grain risk sweep on C3 (best from 8).

C3 = relax(hw_extreme_on, sig_extreme_on) + blackout +H=06-08
   + daily after_close L=$700.

Best from Phase 8 was risk=0.50% on C2c (no daily limit) PnL=$74,718 DD=$1,911.
Try: risk in {0.49, 0.495, 0.50, 0.505, 0.51, 0.515} on C3 to find true max under DD<$2k.

Also two diagnostics:
- C2c at risk=0.505 / 0.510 (without daily limit) for comparison.
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
    START,
    STRATEGY,
    SYMBOL,
)


EXTRA_06_08 = {"start_hour": 6, "start_minute": 0, "end_hour": 8, "end_minute": 0}
RELAX_PARAMS = dict(BASELINE_V4_PARAMS)
RELAX_PARAMS["hw_extreme_on"] = False
RELAX_PARAMS["sig_extreme_on"] = False


def _engine_with(*, loss=None):
    return make_engine_settings(
        STRATEGY,
        extra_active_windows=list(BASELINE_ACTIVE_BLACKOUTS) + [EXTRA_06_08],
        daily_loss_limit=loss,
        daily_limit_mode="after_close",
    )


def _run(label, *, risk, loss=None):
    return bench(
        label,
        strategy_name=STRATEGY,
        symbol=SYMBOL,
        interval=INTERVAL,
        start=START,
        end=END,
        strategy_params=RELAX_PARAMS,
        initial_equity=INITIAL_EQUITY,
        risk_per_trade=risk,
        max_contracts=MAX_CONTRACTS,
        engine_settings=_engine_with(loss=loss),
    )


def main() -> int:
    print("=" * 120)
    print(f"PHASE 8b — Fine risk sweep on the C3 stack")
    print("=" * 120)
    rows = []
    for r in [0.0048, 0.0049, 0.00495, 0.0050, 0.00505, 0.0051, 0.00515, 0.0052]:
        rows.append((f"C3 risk={r*100:.3f}% +L700",
                     _run(f"C3 risk={r*100:.3f}% +L700", risk=r, loss=700)))
    print()
    # diagnostic: no daily limit at same risks
    for r in [0.0050, 0.0051]:
        rows.append((f"C2c risk={r*100:.3f}% (no limit)",
                     _run(f"C2c risk={r*100:.3f}% (no limit)", risk=r)))

    print()
    print("=" * 120)
    print("UNDER DD<$2,000  (sorted by PnL)")
    print("=" * 120)
    valid = sorted(((l, s) for l, s in rows if s["max_dd_$"] < 2000),
                   key=lambda r: -r[1]["net_pnl"])
    print(f"{'Rank':<5}{'Config':<45}{'PnL':>11}{'DD':>9}{'N':>7}{'PF':>7}{'WR':>7}{'P/DD':>8}")
    print("-" * 120)
    for i, (lbl, s) in enumerate(valid):
        ratio = s["net_pnl"] / max(s["max_dd_$"], 1.0)
        print(f"{i+1:<5}{lbl:<45}${s['net_pnl']:>9,.0f}${s['max_dd_$']:>7,.0f}"
              f"{s['trades']:>7}{s['profit_factor']:>7.2f}{s['win_rate']:>6.1f}%{ratio:>8.1f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
