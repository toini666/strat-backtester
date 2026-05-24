"""Phase 8 — max_contracts crawl + module toggles at rr=1.25/lb=15.

Hypothesis: DD spikes might come from large trades or specific module noise.
- Cap max_contracts to limit risk per single trade.
- Disable individual modules (ut, st, ema, alligator, stc) to see if one is
  net-negative at the new low-rr regime.

Also test alternative rr-anchor (rr=1.3/lb=15) DD-reducers.
"""
from __future__ import annotations
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.goals._shared.harness import run_backtest, summarize, fmt_summary
from _campaign import seed_kwargs


ANCHOR = {"rr_tp": 1.25, "sl_lookback": 15}


def bench(label, params=None, max_contracts=20):
    p = dict(ANCHOR)
    if params:
        p.update(params)
    kw = seed_kwargs(params=p, max_contracts=max_contracts)
    r = run_backtest(**kw)
    s = summarize(r)
    s["label"] = label
    print(f"{label:<60s} | {fmt_summary(s)}")
    return s


def main():
    print("--- ANCHOR rr=1.25 lb=15 (max=20) ---")
    anchor = bench("anchor")

    print("\n--- A) max_contracts crawl ---")
    rows = []
    for mc in [5, 8, 10, 12, 15, 18, 20]:
        rows.append(bench(f"max_contracts={mc}", max_contracts=mc))

    print("\n--- B) Module toggles (turn OFF one at a time) ---")
    toggles = [
        ("ut_on=False",         {"ut_on": False}),
        ("st_on=False",         {"st_on": False}),
        ("ema_on=False",        {"ema_on": False}),
        ("alligator_on=False",  {"alligator_on": False}),
        ("stc_on=False",        {"stc_on": False}),
        ("hw_filter_on=False",  {"hw_filter_on": False}),
        ("cloud_filter_on=False", {"cloud_filter_on": False}),
        ("delta_filter_on=False", {"delta_filter_on": False}),
        ("sig_extreme_filter_on=False", {"sig_extreme_filter_on": False}),
    ]
    for label, p in toggles:
        rows.append(bench(label, params=p))

    print("\n--- C) Cooldown bars (might help reduce streak DD) ---")
    for cb in [1, 2, 3, 5]:
        rows.append(bench(f"cooldown_bars={cb}", params={"cooldown_bars": cb}))

    print("\n--- D) Alternative rr_tp=1.3 lb=15 (WR=50.3, DD=$3,122) with DD-reducers ---")
    p = {"rr_tp": 1.3, "sl_lookback": 15}
    rows.append(bench("rr=1.3 lb=15 max=15", params=p, max_contracts=15))
    rows.append(bench("rr=1.3 lb=15 max=18", params=p, max_contracts=18))

    print(f"\nANCHOR: PnL=${anchor['net_pnl']:,.0f}  DD=${anchor['max_dd_$']:,.0f}  WR={anchor['win_rate']:.1f}%")
    print("\n--- ✅ Candidates with WR>=50% AND DD<=2500 ---")
    good = [r for r in rows if r["win_rate"] >= 50.0 and r["max_dd_$"] <= 2500.0]
    good.sort(key=lambda r: r["net_pnl"], reverse=True)
    if good:
        for r in good:
            print(f"  ✅ {r['label']:<48s} WR={r['win_rate']:.1f}%  "
                  f"DD=${r['max_dd_$']:,.0f}  PnL=${r['net_pnl']:,.0f}  N={r['trades']}")
    else:
        print("  (none)")
        print("\n--- Top 8 by smallest DD overshoot at WR>=50% ---")
        close = [r for r in rows if r["win_rate"] >= 50.0]
        close.sort(key=lambda r: r["max_dd_$"])
        for r in close[:8]:
            print(f"  ❌ {r['label']:<48s} WR={r['win_rate']:.1f}%  "
                  f"DD=${r['max_dd_$']:,.0f} (+${r['max_dd_$']-2500:.0f})  PnL=${r['net_pnl']:,.0f}")


if __name__ == "__main__":
    main()
