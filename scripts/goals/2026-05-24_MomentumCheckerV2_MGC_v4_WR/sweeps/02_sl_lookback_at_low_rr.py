"""Phase 2 — sl_lookback re-sweep at low rr_tp.

Memory [[feedback-sl-lookback-rr-interaction]]:
  optimal sl_lookback depends on rr_tp; wider lookback at lower rr.
MGC v3 found sl_lookback=15 unique optimum at rr=3 (the MGC anchor).
On MNQ v5, sl_lookback flipped from 5 to 10 going from rr=2.5 to rr=1.55.

Test: sl_lookback ∈ {5, 7, 10, 12, 15, 18, 20, 25} × {1.55, 1.5} rr_tp.
"""
from __future__ import annotations
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.goals._shared.harness import run_backtest, summarize, fmt_summary
from _campaign import seed_kwargs


LBS = [5, 7, 10, 12, 15, 18, 20, 25]
RRS = [1.55, 1.5]


def main():
    rows = []
    print(f"{'label':<32s} | metrics")
    print("-" * 110)
    for rr in RRS:
        for lb in LBS:
            params = {"rr_tp": rr, "sl_lookback": lb}
            kwargs = seed_kwargs(params=params)
            r = run_backtest(**kwargs)
            s = summarize(r)
            s["rr_tp"] = rr
            s["sl_lookback"] = lb
            rows.append(s)
            label = f"rr={rr}  sl_lb={lb}"
            print(f"{label:<32s} | {fmt_summary(s)}")
        print()

    print("--- Sorted by PnL (top 5 per rr_tp) ---")
    for rr in RRS:
        sub = sorted([r for r in rows if r["rr_tp"] == rr],
                     key=lambda r: r["net_pnl"], reverse=True)[:5]
        for r in sub:
            print(f"  rr={r['rr_tp']}  lb={r['sl_lookback']}  PnL=${r['net_pnl']:,.0f}  "
                  f"DD=${r['max_dd_$']:,.0f}  WR={r['win_rate']:.1f}%  N={r['trades']}")

    print("\n--- Best WR within DD<=2500 ---")
    safe = [r for r in rows if r["max_dd_$"] <= 2500.0]
    for r in sorted(safe, key=lambda r: r["win_rate"], reverse=True)[:5]:
        print(f"  rr={r['rr_tp']}  lb={r['sl_lookback']}  WR={r['win_rate']:.1f}%  "
              f"DD=${r['max_dd_$']:,.0f}  PnL=${r['net_pnl']:,.0f}")


if __name__ == "__main__":
    main()
