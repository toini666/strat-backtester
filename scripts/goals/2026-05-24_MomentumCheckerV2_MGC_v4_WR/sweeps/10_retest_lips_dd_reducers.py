"""Phase 10 — pts_retest_lips=0 + DD reducers (path 1 from Phase 9).

Path 1: rr=1.25 lb=15 pts_retest_lips=0 → WR=51.2% DD=$3,630 PnL=$33,053 (DD +$1,130).
Need to cut DD by $1,130 while keeping WR>=50.

Test:
A) max_contracts crawl
B) risk_per_trade crawl
C) BO additions
D) sl_lookback re-tune
E) tick_buffer
F) Combine top
"""
from __future__ import annotations
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.goals._shared.harness import run_backtest, summarize, fmt_summary
from _campaign import seed_kwargs, build_engine_settings, SEED_BLACKOUTS_ACTIVE


ANCHOR = {"rr_tp": 1.25, "sl_lookback": 15, "pts_retest_lips": 0}


def bench(label, params=None, risk=None, max_contracts=20, bos=None):
    p = dict(ANCHOR)
    if params:
        p.update(params)
    kw = seed_kwargs(params=p, max_contracts=max_contracts)
    if risk is not None:
        kw["risk_per_trade"] = risk
    if bos is not None:
        kw["engine_settings"] = build_engine_settings(bos)
    r = run_backtest(**kw)
    s = summarize(r)
    s["label"] = label
    print(f"{label:<60s} | {fmt_summary(s)}")
    return s


def main():
    print("--- ANCHOR rr=1.25 lb=15 pts_retest_lips=0 ---")
    a = bench("anchor")

    print("\n--- A) max_contracts crawl ---")
    rows = []
    for mc in [3, 5, 7, 10, 12, 15]:
        rows.append(bench(f"max_contracts={mc}", max_contracts=mc))

    print("\n--- B) risk crawl ---")
    for r_pct in [0.50, 0.48, 0.45, 0.42, 0.40, 0.38, 0.35]:
        rows.append(bench(f"risk={r_pct}%", risk=r_pct / 100.0))

    print("\n--- C) BO single additions ---")
    additions = [
        ("+ BO 7-8",      [(7, 0, 8, 0)]),
        ("+ BO 11-12",    [(11, 0, 12, 0)]),
        ("+ BO 12-12:30", [(12, 0, 12, 30)]),
        ("+ BO 17-18",    [(17, 0, 18, 0)]),
        ("+ BO 1-2",      [(1, 0, 2, 0)]),
        ("+ BO 19-20",    [(19, 0, 20, 0)]),
    ]
    for label, addn in additions:
        bos = list(SEED_BLACKOUTS_ACTIVE) + addn
        rows.append(bench(label, bos=bos))

    print("\n--- D) sl_lookback re-tune at this anchor ---")
    for lb in [10, 12, 13, 14, 16, 18, 20]:
        rows.append(bench(f"lb={lb}", params={"sl_lookback": lb}))

    print("\n--- E) tick_buffer ---")
    for tb in [0, 1, 3]:
        rows.append(bench(f"tb={tb}", params={"tick_buffer": tb}))

    print("\n--- F) Combinations: low risk + max_contracts + BO ---")
    bos_1112 = list(SEED_BLACKOUTS_ACTIVE) + [(11, 0, 12, 0)]
    rows.append(bench("risk=0.42% max=10 + BO 11-12", risk=0.0042, max_contracts=10, bos=bos_1112))
    rows.append(bench("risk=0.45% max=10 + BO 11-12", risk=0.0045, max_contracts=10, bos=bos_1112))
    rows.append(bench("risk=0.42% max=15", risk=0.0042, max_contracts=15))
    rows.append(bench("risk=0.45% max=15", risk=0.0045, max_contracts=15))
    rows.append(bench("risk=0.42% lb=12", risk=0.0042, params={"sl_lookback": 12}))
    rows.append(bench("risk=0.40% lb=12", risk=0.0040, params={"sl_lookback": 12}))
    rows.append(bench("risk=0.42% lb=13", risk=0.0042, params={"sl_lookback": 13}))

    print(f"\nANCHOR: PnL=${a['net_pnl']:,.0f}  DD=${a['max_dd_$']:,.0f}  WR={a['win_rate']:.1f}%")
    print("\n--- ✅ WR>=50% AND DD<=2500 (sorted by PnL desc) ---")
    good = [r for r in rows if r["win_rate"] >= 50.0 and r["max_dd_$"] <= 2500.0]
    good.sort(key=lambda r: r["net_pnl"], reverse=True)
    if good:
        for r in good[:15]:
            print(f"  ✅ {r['label']:<46s} WR={r['win_rate']:.1f}%  "
                  f"DD=${r['max_dd_$']:,.0f}  PnL=${r['net_pnl']:,.0f}  N={r['trades']}")
    else:
        print("  (none)")
        print("\n--- Top 8 smallest DD overshoot at WR>=50% ---")
        close = [r for r in rows if r["win_rate"] >= 50.0]
        close.sort(key=lambda r: r["max_dd_$"])
        for r in close[:8]:
            print(f"  ❌ {r['label']:<46s} WR={r['win_rate']:.1f}%  "
                  f"DD=${r['max_dd_$']:,.0f} (+{r['max_dd_$']-2500:.0f})  PnL=${r['net_pnl']:,.0f}")


if __name__ == "__main__":
    main()
