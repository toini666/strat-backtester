"""Phase 5 — rr_tp × sl_lookback grid at lower rr values.

Phase 1 showed rr_tp=1.25 (seed lb=15) gives WR=50.7%, DD=$2,913 — closest to goal.
Phase 2 showed sl_lookback=12 reduces DD at rr=1.55.
This phase grids the two together at lower rr_tp.

Also test tick_buffer=1 (Phase 3 small win) on the winners.
"""
from __future__ import annotations
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.goals._shared.harness import run_backtest, summarize, fmt_summary
from _campaign import seed_kwargs


def bench(label, params):
    r = run_backtest(**seed_kwargs(params=params))
    s = summarize(r)
    s["label"] = label
    s.update(params)
    print(f"{label:<46s} | {fmt_summary(s)}")
    return s


def main():
    print("--- rr_tp × sl_lookback grid (lower rr) ---")
    rrs = [1.45, 1.4, 1.35, 1.3, 1.25, 1.2, 1.15, 1.1]
    lbs = [10, 12, 15]
    rows = []
    for rr in rrs:
        for lb in lbs:
            p = {"rr_tp": rr, "sl_lookback": lb}
            rows.append(bench(f"rr={rr} lb={lb}", p))
        print()

    # WR>=50% candidates
    print("--- WR >= 50% candidates ---")
    cand = [r for r in rows if r["win_rate"] >= 50.0]
    cand.sort(key=lambda r: (r["max_dd_$"], -r["net_pnl"]))
    for r in cand:
        ok = "✅" if r["max_dd_$"] <= 2500 else "❌"
        print(f"  {ok} rr={r['rr_tp']} lb={r['sl_lookback']}  WR={r['win_rate']:.1f}%  "
              f"DD=${r['max_dd_$']:,.0f}  PnL=${r['net_pnl']:,.0f}")


if __name__ == "__main__":
    main()
