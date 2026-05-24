"""Phase 6 — risk crawl + DD-reducing BOs on rr=1.25/lb=15 anchor.

Phase 5 best: rr=1.25/lb=15 WR=50.7% DD=$2,913 PnL=$33,833. Over DD by $413.

Two complementary levers to bring DD to $2,500:
A) risk_per_trade crawl (mechanical DD scaler).
B) BO additions on low-WR/-PnL hours (might surgically remove worst losing
   streak without killing PnL much).

Then combine the best of A and B.
"""
from __future__ import annotations
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.goals._shared.harness import run_backtest, summarize, fmt_summary
from scripts.goals._shared.analysis import bucket_by_hour
from _campaign import seed_kwargs, build_engine_settings, SEED_BLACKOUTS_ACTIVE


ANCHOR = {"rr_tp": 1.25, "sl_lookback": 15}


def bench(label, params=None, risk=None, bos=None):
    p = dict(ANCHOR)
    if params:
        p.update(params)
    kw = seed_kwargs(params=p)
    if risk is not None:
        kw["risk_per_trade"] = risk
    if bos is not None:
        kw["engine_settings"] = build_engine_settings(bos)
    r = run_backtest(**kw)
    s = summarize(r)
    s["label"] = label
    print(f"{label:<54s} | {fmt_summary(s)}")
    s["_r"] = r
    return s


def main():
    print("--- ANCHOR rr=1.25 lb=15 (seed risk 0.53%) ---")
    anchor = bench("anchor")

    # Hour buckets at this anchor
    print("\n--- HOUR BUCKETS ---")
    h = bucket_by_hour(anchor["_r"]["trades"])
    print(f"{'H':>3}  {'N':>4}  {'WR%':>6}  {'Total':>10}")
    for hr in sorted(h):
        b = h[hr]
        marker = "  *LO*" if b['win_rate'] < 40 else ("  *NEG*" if b['total'] < 0 else "")
        print(f"{hr:>3}  {b['n']:>4}  {b['win_rate']:>6.1f}  {b['total']:>10.2f}{marker}")

    print("\n--- A) risk_per_trade crawl ---")
    risk_rows = []
    for r_pct in [0.50, 0.48, 0.46, 0.44, 0.42, 0.40, 0.38]:
        risk_rows.append(bench(f"risk={r_pct}%", risk=r_pct / 100.0))

    print("\n--- B) DD-reducing BO additions (1 at a time) ---")
    bo_rows = []
    additions = [
        ("+ BO 7-8",      [(7, 0, 8, 0)]),
        ("+ BO 11-12",    [(11, 0, 12, 0)]),
        ("+ BO 12-12:30", [(12, 0, 12, 30)]),
        ("+ BO 14-15",    [(14, 0, 15, 0)]),
        ("+ BO 17-18",    [(17, 0, 18, 0)]),
        ("+ BO 19-20",    [(19, 0, 20, 0)]),
    ]
    for label, addn in additions:
        bos = list(SEED_BLACKOUTS_ACTIVE) + addn
        bo_rows.append(bench(label, bos=bos))

    print("\n--- Best A or B sorted by (WR>=50 ∧ DD<=2500) ---")
    all_rows = risk_rows + bo_rows
    good = [r for r in all_rows if r["win_rate"] >= 50.0 and r["max_dd_$"] <= 2500.0]
    good.sort(key=lambda r: r["net_pnl"], reverse=True)
    if good:
        for r in good:
            print(f"  ✅ {r['label']:<35s} WR={r['win_rate']:.1f}%  "
                  f"DD=${r['max_dd_$']:,.0f}  PnL=${r['net_pnl']:,.0f}")
    else:
        print("  (no single lever passes both constraints)")
        # Show closest (smallest DD overshoot at WR>=50)
        close = [r for r in all_rows if r["win_rate"] >= 50.0]
        close.sort(key=lambda r: r["max_dd_$"])
        for r in close[:5]:
            print(f"  ❌ {r['label']:<35s} WR={r['win_rate']:.1f}%  "
                  f"DD=${r['max_dd_$']:,.0f} (+${r['max_dd_$']-2500:.0f})  PnL=${r['net_pnl']:,.0f}")


if __name__ == "__main__":
    main()
