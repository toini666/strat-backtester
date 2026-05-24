"""Phase 1b — minimal-modules anchor + rr_tp sweep (per user instruction).

User: *"N'hesite pas a repartir d'une base ou tres peu de conditions sont activees."*

MGC v3 concluded all modules needed at rr=3, but the regime is different at low rr.
We test: osc+hma only (cores) at multiple rr_tp values. If any cell beats the
seed-anchor Pareto (PnL given WR>=50% & DD<=2500), we adopt it.

Filters off here:
  ema_on, st_on, alligator_on, ut_on, stc_on = False
  hw_filter_on, sig_*_on, cloud_*_on, delta_*_on = False
Cores kept ON:
  osc_on, hma_on
"""
from __future__ import annotations
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.goals._shared.harness import run_backtest, summarize, fmt_summary
from _campaign import seed_kwargs, MINIMAL_PARAMS_OVERRIDE


RR_VALUES = [3.0, 2.5, 2.0, 1.55, 1.25, 1.0]


def main():
    print("--- MINIMAL MODULES (osc + hma only) ---")
    print(f"{'label':<32s} | metrics")
    print("-" * 110)
    rows = []
    for rr in RR_VALUES:
        params = dict(MINIMAL_PARAMS_OVERRIDE)
        params["rr_tp"] = rr
        kwargs = seed_kwargs(params=params)
        r = run_backtest(**kwargs)
        s = summarize(r)
        s["rr_tp"] = rr
        rows.append(s)
        label = f"MIN rr_tp={rr}"
        print(f"{label:<32s} | {fmt_summary(s)}")

    print()
    print("--- Candidates with WR >= 50% AND DD <= 2500 ---")
    cand = [r for r in rows if r["win_rate"] >= 50.0 and r["max_dd_$"] <= 2500.0]
    if not cand:
        print("  (none)")
    else:
        for r in cand:
            print(f"  rr={r['rr_tp']}  WR={r['win_rate']:.1f}%  DD=${r['max_dd_$']:,.0f}  PnL=${r['net_pnl']:,.0f}")


if __name__ == "__main__":
    main()
