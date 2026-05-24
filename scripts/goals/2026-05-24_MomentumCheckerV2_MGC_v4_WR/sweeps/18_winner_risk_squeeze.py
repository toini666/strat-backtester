"""Phase 18 — Risk squeeze on WINNER cell.

Advisor lead: tb=0 + lb=14 + risk > 0.40% might stay in the DD=$2,278 rounding cell.
If yes, free PnL upside.
"""
from __future__ import annotations
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.goals._shared.harness import run_backtest, summarize, fmt_summary
from _campaign import seed_kwargs, build_engine_settings, SEED_BLACKOUTS_ACTIVE


WINNER_BASE = {"rr_tp": 1.25, "ut_on": False, "sl_lookback": 14, "tick_buffer": 0}
WINNER_BOS = list(SEED_BLACKOUTS_ACTIVE) + [(7, 0, 8, 0), (12, 0, 12, 30)]


def bench(label, risk):
    kw = seed_kwargs(params=WINNER_BASE)
    kw["risk_per_trade"] = risk
    kw["engine_settings"] = build_engine_settings(WINNER_BOS)
    r = run_backtest(**kw)
    s = summarize(r)
    raw = r["metrics"]["max_drawdown_dollars"]
    s["label"] = label
    print(f"{label:<22s} | {fmt_summary(s)}  rawDD=${raw:.2f}")
    return s


def main():
    print("--- Risk squeeze at WINNER base (tb=0 lb=14 + BOs) ---")
    rows = []
    for r_pct in [0.40, 0.405, 0.41, 0.415, 0.42, 0.425, 0.43, 0.44, 0.45]:
        rows.append(bench(f"risk={r_pct}%", r_pct / 100.0))

    print("\n--- ✅ WR>=50% AND DD<2500 STRICT ---")
    good = [r for r in rows if r["win_rate"] >= 50.0 and r["max_dd_$"] < 2500.0]
    good.sort(key=lambda r: r["net_pnl"], reverse=True)
    for r in good:
        print(f"  ✅ {r['label']:<18s} WR={r['win_rate']:.1f}% DD=${r['max_dd_$']:,.0f} "
              f"PnL=${r['net_pnl']:,.0f} N={r['trades']}")


if __name__ == "__main__":
    main()
