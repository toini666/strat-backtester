"""Phase 1 — rr_tp sweep on seed (the main WR lever).

Math (MCV2 has tp1_full_exit=True):
  break_even_WR = 1 / (1 + rr_tp)
  Seed: rr=3 -> BE_WR=25%, observed WR=39.6% -> edge=+14.6 pp.
  Expected WR at rr=X = 1/(1+X) + 14.6 pp (first-order).

Test:
  rr_tp ∈ {3.0 (seed), 2.5, 2.0, 1.75, 1.6, 1.55, 1.5, 1.4, 1.25, 1.0}.

We keep be_at_rr=2 (seed). At rr<2 the BE trigger lies BEYOND TP -> inert,
so no harm; this isolates rr_tp's effect cleanly.
"""
from __future__ import annotations
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.goals._shared.harness import run_backtest, summarize, fmt_summary
from _campaign import seed_kwargs


RR_VALUES = [3.0, 2.5, 2.0, 1.75, 1.6, 1.55, 1.5, 1.4, 1.25, 1.0]


def main():
    print(f"{'label':<32s} | metrics")
    print("-" * 110)
    rows = []
    for rr in RR_VALUES:
        kwargs = seed_kwargs(params={"rr_tp": rr})
        r = run_backtest(**kwargs)
        s = summarize(r)
        s["rr_tp"] = rr
        s["be_wr_pct"] = 100.0 / (1.0 + rr)
        rows.append(s)
        label = f"rr_tp={rr}  BE_WR={s['be_wr_pct']:.1f}%"
        print(f"{label:<32s} | {fmt_summary(s)}")

    print()
    print("--- Candidates with WR >= 50% AND DD <= 2500 ---")
    cand = [r for r in rows if r["win_rate"] >= 50.0 and r["max_dd_$"] <= 2500.0]
    for r in cand:
        print(f"  rr={r['rr_tp']}  WR={r['win_rate']:.1f}%  DD=${r['max_dd_$']:,.0f}  PnL=${r['net_pnl']:,.0f}")

    print()
    print("--- Best PnL with WR >= 50% (any DD): ---")
    wr_ok = [r for r in rows if r["win_rate"] >= 50.0]
    if wr_ok:
        best = max(wr_ok, key=lambda r: r["net_pnl"])
        print(f"  rr={best['rr_tp']}  WR={best['win_rate']:.1f}%  DD=${best['max_dd_$']:,.0f}  PnL=${best['net_pnl']:,.0f}")
    else:
        print("  (none pass 50% WR with seed params)")


if __name__ == "__main__":
    main()
