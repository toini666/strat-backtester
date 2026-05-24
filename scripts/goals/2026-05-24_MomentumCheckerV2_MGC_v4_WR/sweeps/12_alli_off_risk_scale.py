"""Phase 12 — alligator_OFF risk scale-up.

Anchor: rr=1.25 lb=15 alligator_off — PnL=$4,440 DD=$1,163 WR=54.5% N=99.
Path: scale risk while staying under DD=$2,500 budget.

Variants:
- Best lb at alli_off was lb=10 (PnL=$5,198 DD=$1,151).
- rr=1.3 was PnL=$4,984 DD=$1,142.
- All have N≈99 (very selective).
"""
from __future__ import annotations
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.goals._shared.harness import run_backtest, summarize, fmt_summary
from _campaign import seed_kwargs


def bench(label, params, risk, max_contracts=20):
    kw = seed_kwargs(params=params, max_contracts=max_contracts)
    kw["risk_per_trade"] = risk
    r = run_backtest(**kw)
    s = summarize(r)
    s["label"] = label
    print(f"{label:<58s} | {fmt_summary(s)}")
    return s


def main():
    # Best alligator-off variants from Phase 9
    variants = {
        "alli_off rr=1.25 lb=10":   {"rr_tp": 1.25, "sl_lookback": 10, "alligator_on": False},
        "alli_off rr=1.25 lb=12":   {"rr_tp": 1.25, "sl_lookback": 12, "alligator_on": False},
        "alli_off rr=1.25 lb=15":   {"rr_tp": 1.25, "sl_lookback": 15, "alligator_on": False},
        "alli_off rr=1.3 lb=15":    {"rr_tp": 1.3,  "sl_lookback": 15, "alligator_on": False},
        "alli_off rr=1.3 lb=10":    {"rr_tp": 1.3,  "sl_lookback": 10, "alligator_on": False},
    }
    risks = [0.0080, 0.0100, 0.0120, 0.0140, 0.0160, 0.0180, 0.0200]
    rows = []
    for label, p in variants.items():
        print(f"\n--- {label} ---")
        for r_dec in risks:
            r_pct = r_dec * 100
            rows.append(bench(f"risk={r_pct:.2f}% {label}", p, r_dec))

    print("\n--- ✅ WR>=50% AND DD<=2500 (sorted by PnL desc) ---")
    good = [r for r in rows if r["win_rate"] >= 50.0 and r["max_dd_$"] <= 2500.0]
    good.sort(key=lambda r: r["net_pnl"], reverse=True)
    for r in good[:20]:
        print(f"  ✅ {r['label']:<54s} WR={r['win_rate']:.1f}%  "
              f"DD=${r['max_dd_$']:,.0f}  PnL=${r['net_pnl']:,.0f}  N={r['trades']}")


if __name__ == "__main__":
    main()
