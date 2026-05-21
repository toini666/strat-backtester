"""Phase 1 — sl_max_points × risk cliff-shift sweep.

Background: the MNQ v3 campaign discovered the int(contracts) cliff can be
SHIFTED by changing sl_max_points. The prior MGC campaign declared
DD < $2,000 "structurally infeasible" because every sub-$2k attempt landed
at a 1-contract floor (~$2,500-$2,700). Shifting sl_max may move that floor.

Seed: sl_max=100, risk=0.55% → DD=$2,486.
We test sl_max ∈ {30, 40, 50, 60, 70, 80, 90, 100, 120, 150} × risk in
0.005% steps from 0.30% to 0.70%, looking for any (sl_max, risk) cell where:
  - DD < $2,000 (stretch target), OR
  - DD < $2,300 with PnL ≥ $58k

This is the highest-leverage phase. ~80 sims.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

CAMPAIGN_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CAMPAIGN_DIR / "sweeps"))

from scripts.goals._shared.harness import run_backtest, summarize, fmt_summary  # noqa: E402

from _campaign import (  # noqa: E402
    BASELINE_PARAMS, END, INITIAL_EQUITY, INTERVAL, MAX_CONTRACTS,
    START, STRATEGY, SYMBOL, seed_engine, SEED_PNL, SEED_DD, DD_HARD_CAP, DD_SOFT_TARGET,
)


def main() -> int:
    print("=" * 110)
    print("PHASE 1 — sl_max_points × risk cliff-shift sweep")
    print("=" * 110)
    print(f"Seed: sl_max=100, risk=0.55% → PnL=${SEED_PNL:,.0f} DD=${SEED_DD:,.0f}")
    print()

    SL_MAXES = [30, 40, 50, 60, 70, 80, 90, 100, 120, 150]
    RISKS = [0.0030, 0.0035, 0.0040, 0.0045, 0.0050, 0.0053, 0.0055, 0.0058,
             0.0060, 0.0063, 0.0065, 0.0070]

    results = []
    t_start = time.time()
    n_total = len(SL_MAXES) * len(RISKS)
    n_done = 0

    for sl_max in SL_MAXES:
        for risk in RISKS:
            n_done += 1
            params = dict(BASELINE_PARAMS)
            params["sl_max_points"] = float(sl_max)
            r = run_backtest(
                strategy_name=STRATEGY, symbol=SYMBOL, interval=INTERVAL,
                start=START, end=END,
                initial_equity=INITIAL_EQUITY, risk_per_trade=risk,
                max_contracts=MAX_CONTRACTS,
                engine_settings=seed_engine(),
                strategy_params=params,
            )
            s = summarize(r)
            s["sl_max"] = sl_max
            s["risk"] = risk
            results.append(s)
            tag = ""
            if s["max_dd_$"] < DD_SOFT_TARGET:
                tag = " ⭐ DD<$2k"
            elif s["max_dd_$"] < 2300 and s["net_pnl"] >= 58_000:
                tag = " ✨ Pareto"
            elif s["max_dd_$"] < DD_HARD_CAP and s["net_pnl"] >= 58_000:
                tag = " ✓"
            print(f"[{n_done:>3}/{n_total}] sl_max={sl_max:>3} r={risk*100:>4.2f}%  {fmt_summary(s)}{tag}")

    elapsed = time.time() - t_start
    print(f"\n{n_total} sims in {elapsed/60:.1f}min ({elapsed/n_total:.1f}s/sim)")

    # Filter for goal-relevant cells
    print("\n" + "=" * 110)
    print("CELLS WITH DD < $2,500 (sorted by PnL desc, then DD asc)")
    print("=" * 110)
    feasible = [s for s in results if s["max_dd_$"] < DD_HARD_CAP]
    feasible.sort(key=lambda s: (-s["net_pnl"], s["max_dd_$"]))
    for s in feasible[:25]:
        print(f"  sl_max={s['sl_max']:>3}  r={s['risk']*100:>4.2f}%  PnL=${s['net_pnl']:>9,.0f}  DD=${s['max_dd_$']:>6,.0f}  P/DD={s['net_pnl']/s['max_dd_$']:.2f}  N={s['trades']}")

    print("\n" + "=" * 110)
    print("CELLS WITH DD < $2,000 (stretch target)")
    print("=" * 110)
    stretch = [s for s in results if s["max_dd_$"] < DD_SOFT_TARGET]
    if not stretch:
        print("  (none)")
    else:
        stretch.sort(key=lambda s: (-s["net_pnl"], s["max_dd_$"]))
        for s in stretch:
            print(f"  sl_max={s['sl_max']:>3}  r={s['risk']*100:>4.2f}%  PnL=${s['net_pnl']:>9,.0f}  DD=${s['max_dd_$']:>6,.0f}  P/DD={s['net_pnl']/s['max_dd_$']:.2f}  N={s['trades']}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
