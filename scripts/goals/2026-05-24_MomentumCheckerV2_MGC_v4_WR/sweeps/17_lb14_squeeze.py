"""Phase 17 — lb=14 squeeze (last push for max PnL).

Phase 16 found lb=14 anchor:
  ut_off rr=1.25 lb=14 risk=0.40% + BO 7-8 + BO 12-12:30
  → PnL=$27,583 DD=$2,551 WR=51.0% N=1047  (over DD by $51)

Tight risk crawl + tick_buffer to find DD under $2,500.
"""
from __future__ import annotations
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.goals._shared.harness import run_backtest, summarize, fmt_summary
from _campaign import seed_kwargs, build_engine_settings, SEED_BLACKOUTS_ACTIVE


BASE = {"rr_tp": 1.25, "ut_on": False, "sl_lookback": 14}
BO_DOUBLE = list(SEED_BLACKOUTS_ACTIVE) + [(12, 0, 12, 30), (7, 0, 8, 0)]


def bench(label, params=None, risk=0.0040, bos=BO_DOUBLE):
    p = dict(BASE)
    if params:
        p.update(params)
    kw = seed_kwargs(params=p)
    kw["risk_per_trade"] = risk
    kw["engine_settings"] = build_engine_settings(bos)
    r = run_backtest(**kw)
    s = summarize(r)
    s["label"] = label
    raw = r["metrics"]["max_drawdown_dollars"]
    print(f"{label:<60s} | {fmt_summary(s)}  rawDD=${raw:.2f}")
    return s


def main():
    rows = []
    print("--- risk crawl at lb=14 ---")
    for r_pct in [0.35, 0.36, 0.37, 0.38, 0.39, 0.40, 0.41, 0.42]:
        rows.append(bench(f"risk={r_pct}%", risk=r_pct / 100.0))

    print("\n--- tick_buffer at lb=14 risk=0.4% ---")
    for tb in [0, 1, 3]:
        rows.append(bench(f"tb={tb} (lb=14 risk=0.4%)", params={"tick_buffer": tb}))

    print("\n--- tick_buffer + risk variations ---")
    for tb in [1, 3]:
        for r_pct in [0.36, 0.38, 0.40]:
            rows.append(bench(f"tb={tb} risk={r_pct}%",
                              params={"tick_buffer": tb}, risk=r_pct / 100.0))

    print("\n--- Add 3rd BO (BO 11-12) ---")
    bos3 = BO_DOUBLE + [(11, 0, 12, 0)]
    for r_pct in [0.40, 0.42, 0.44]:
        rows.append(bench(f"3BO risk={r_pct}%", risk=r_pct / 100.0, bos=bos3))

    print("\n--- ✅ WR>=50% AND DD<=2500 (sorted by PnL desc) ---")
    good = [r for r in rows if r["win_rate"] >= 50.0 and r["max_dd_$"] <= 2500.0]
    good.sort(key=lambda r: r["net_pnl"], reverse=True)
    for r in good[:12]:
        print(f"  ✅ {r['label']:<52s} WR={r['win_rate']:.1f}%  "
              f"DD=${r['max_dd_$']:,.0f}  PnL=${r['net_pnl']:,.0f}  N={r['trades']}")


if __name__ == "__main__":
    main()
