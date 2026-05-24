"""Phase 11 — min_gap=6 alligator_off risk crawl (advisor lead).

Phase 9 D found: min_gap=6 alligator_off rr=1.25 lb=15
  → PnL=$39,517 DD=$5,615 WR=50.2% N=1111

DD over budget by $3,115. Linear projection: risk reduction ~halving (0.53→0.24%)
should bring DD to $2,500. PnL would project to ~$17-18k — 2× the alligator-off
pure path.

Also: dump max-DD trade date to check for single-streak fix.
"""
from __future__ import annotations
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd
from scripts.goals._shared.harness import run_backtest, summarize, fmt_summary
from _campaign import seed_kwargs


ANCHOR = {"rr_tp": 1.25, "sl_lookback": 15, "alligator_on": False, "min_gap": 6}


def bench(label, params=None, risk=None, max_contracts=20):
    p = dict(ANCHOR)
    if params:
        p.update(params)
    kw = seed_kwargs(params=p, max_contracts=max_contracts)
    if risk is not None:
        kw["risk_per_trade"] = risk
    r = run_backtest(**kw)
    s = summarize(r)
    s["label"] = label
    s["_r"] = r
    print(f"{label:<60s} | {fmt_summary(s)}")
    return s


def dump_max_dd_period(result):
    """Walk equity curve, find peak-to-trough (in $) and report dates."""
    eq = result["equity_curve"]
    if not eq:
        print("  (no equity curve)")
        return
    if isinstance(eq[0], dict):
        # Try common key names
        keys = list(eq[0].keys())
        ts_key = next((k for k in ["time", "timestamp", "date"] if k in keys), keys[0])
        val_key = next((k for k in ["equity", "value", "balance", "pnl"] if k in keys), keys[-1])
        ts = [pd.to_datetime(p[ts_key]) for p in eq]
        vals = [float(p[val_key]) for p in eq]
    else:
        ts = list(range(len(eq)))
        vals = [float(v) for v in eq]
    peak = vals[0]
    peak_t = ts[0]
    max_dd = 0.0
    dd_peak_t = ts[0]
    dd_trough_t = ts[0]
    for t, v in zip(ts, vals):
        if v > peak:
            peak = v
            peak_t = t
        dd = peak - v
        if dd > max_dd:
            max_dd = dd
            dd_peak_t = peak_t
            dd_trough_t = t
    print(f"  Max DD ${max_dd:,.0f} from {dd_peak_t} to {dd_trough_t}")


def main():
    print("--- ANCHOR rr=1.25 lb=15 alli_off min_gap=6 (risk=0.53%) ---")
    a = bench("anchor")
    print()
    dump_max_dd_period(a["_r"])

    print("\n--- A) Risk crawl ---")
    rows = []
    for r_pct in [0.18, 0.20, 0.22, 0.24, 0.26, 0.28, 0.30, 0.32, 0.35, 0.40, 0.45]:
        rows.append(bench(f"risk={r_pct}%", risk=r_pct / 100.0))

    print("\n--- B) Risk crawl + max_contracts cap ---")
    for r_pct, mc in [(0.30, 5), (0.30, 8), (0.30, 10), (0.40, 5), (0.40, 8)]:
        rows.append(bench(f"risk={r_pct}% max={mc}", risk=r_pct/100.0, max_contracts=mc))

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
        print("\n--- Top 5 closest at WR>=50% ---")
        close = [r for r in rows if r["win_rate"] >= 50.0]
        close.sort(key=lambda r: r["max_dd_$"])
        for r in close[:5]:
            print(f"  ❌ {r['label']:<46s} WR={r['win_rate']:.1f}%  "
                  f"DD=${r['max_dd_$']:,.0f} (+{r['max_dd_$']-2500:.0f})  PnL=${r['net_pnl']:,.0f}")


if __name__ == "__main__":
    main()
