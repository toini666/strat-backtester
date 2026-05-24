"""Phase 16 — Push WINNER PnL with BO 7-8 DD headroom (advisor lesson:
'check rr_tp at final anchor — moved cliff').

Anchor: ut_off rr=1.25 lb=13 risk=0.4% + BO 12-12:30 + BO 7-8
  Phase 15: PnL=$25,779 DD=$2,319 WR=50.8% N=1085  ($181 DD headroom)

Test:
- risk crawl up
- rr_tp recheck at this final anchor (Phase 7 advisor logic)
- 2 BO + 12-12:30 wider
"""
from __future__ import annotations
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.goals._shared.harness import run_backtest, summarize, fmt_summary
from _campaign import seed_kwargs, build_engine_settings, SEED_BLACKOUTS_ACTIVE


BASE = {"rr_tp": 1.25, "ut_on": False, "sl_lookback": 13}
BO_DOUBLE = list(SEED_BLACKOUTS_ACTIVE) + [(12, 0, 12, 30), (7, 0, 8, 0)]


def bench(label, params=None, risk=0.0040, max_contracts=20, bos=BO_DOUBLE):
    p = dict(BASE)
    if params:
        p.update(params)
    kw = seed_kwargs(params=p, max_contracts=max_contracts)
    kw["risk_per_trade"] = risk
    kw["engine_settings"] = build_engine_settings(bos)
    r = run_backtest(**kw)
    s = summarize(r)
    s["label"] = label
    raw_dd = r["metrics"]["max_drawdown_dollars"]
    print(f"{label:<60s} | {fmt_summary(s)}  rawDD=${raw_dd:.2f}")
    return s


def main():
    print("--- Anchor (BO double 7-8 + 12-12:30) ---")
    a = bench("anchor")

    print("\n--- A) risk crawl up (DD headroom) ---")
    rows = []
    for r_pct in [0.40, 0.41, 0.42, 0.43, 0.44, 0.45, 0.46, 0.47, 0.48]:
        rows.append(bench(f"risk={r_pct}%", risk=r_pct / 100.0))

    print("\n--- B) rr_tp recheck at final anchor (advisor: cliff moves) ---")
    for rr in [1.1, 1.15, 1.2, 1.25, 1.3, 1.35, 1.4]:
        rows.append(bench(f"rr={rr}", params={"rr_tp": rr}))

    print("\n--- C) sl_lookback recheck at final anchor ---")
    for lb in [10, 12, 13, 14, 15]:
        rows.append(bench(f"lb={lb}", params={"sl_lookback": lb}))

    print("\n--- D) tick_buffer at final anchor ---")
    for tb in [0, 1, 3]:
        rows.append(bench(f"tb={tb}", params={"tick_buffer": tb}))

    print("\n--- E) combos: risk × rr ---")
    for rr in [1.2, 1.3]:
        for r_pct in [0.40, 0.42, 0.44]:
            rows.append(bench(f"rr={rr} risk={r_pct}%",
                              params={"rr_tp": rr}, risk=r_pct / 100.0))

    print(f"\nANCHOR: PnL=${a['net_pnl']:,.0f}  DD=${a['max_dd_$']:,.0f}  WR={a['win_rate']:.1f}%")
    print("\n--- ✅ WR>=50% AND DD<=2500 (sorted by PnL desc) — top 15 ---")
    good = [r for r in rows if r["win_rate"] >= 50.0 and r["max_dd_$"] <= 2500.0]
    good.sort(key=lambda r: r["net_pnl"], reverse=True)
    for r in good[:15]:
        print(f"  ✅ {r['label']:<52s} WR={r['win_rate']:.1f}%  "
              f"DD=${r['max_dd_$']:,.0f}  PnL=${r['net_pnl']:,.0f}  N={r['trades']}")


if __name__ == "__main__":
    main()
