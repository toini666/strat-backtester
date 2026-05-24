"""Phase 14 — Tight sweep around ut_off risk=0.40% lb=14 (Phase 13 best).

Phase 13: risk=0.40% ut_off lb=14 → DD=$2,648 (over $148) PnL=$29,018 WR=50.9%
                                       PnL=$33,657 at risk=0.53% DD $3,197.

Tight sweep:
- risk ∈ {0.36, 0.37, 0.38, 0.39, 0.40, 0.41, 0.42}
- lb ∈ {13, 14, 15}
- BO additions (single window)
- tick_buffer {0, 1, 2, 3}
- max_contracts cap
"""
from __future__ import annotations
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.goals._shared.harness import run_backtest, summarize, fmt_summary
from _campaign import seed_kwargs, build_engine_settings, SEED_BLACKOUTS_ACTIVE


ANCHOR = {"rr_tp": 1.25, "ut_on": False}


def bench(label, params, risk, max_contracts=20, bos=None):
    p = dict(ANCHOR)
    p.update(params)
    kw = seed_kwargs(params=p, max_contracts=max_contracts)
    kw["risk_per_trade"] = risk
    if bos is not None:
        kw["engine_settings"] = build_engine_settings(bos)
    r = run_backtest(**kw)
    s = summarize(r)
    s["label"] = label
    print(f"{label:<62s} | {fmt_summary(s)}")
    return s


def main():
    print("--- Tight risk × lb grid at ut_off ---")
    rows = []
    for lb in [13, 14, 15]:
        for r_pct in [0.36, 0.37, 0.38, 0.39, 0.40, 0.41, 0.42]:
            rows.append(bench(f"risk={r_pct}% lb={lb}",
                              {"sl_lookback": lb}, r_pct / 100.0))
        print()

    print("\n--- + BO 12-12:30 on the close cells ---")
    bos_1230 = list(SEED_BLACKOUTS_ACTIVE) + [(12, 0, 12, 30)]
    for r_pct in [0.36, 0.38, 0.40, 0.42]:
        for lb in [13, 14]:
            rows.append(bench(f"risk={r_pct}% lb={lb} + BO 12-12:30",
                              {"sl_lookback": lb}, r_pct / 100.0, bos=bos_1230))

    print("\n--- + BO 11-12 on close cells ---")
    bos_1112 = list(SEED_BLACKOUTS_ACTIVE) + [(11, 0, 12, 0)]
    for r_pct in [0.36, 0.40]:
        for lb in [13, 14]:
            rows.append(bench(f"risk={r_pct}% lb={lb} + BO 11-12",
                              {"sl_lookback": lb}, r_pct / 100.0, bos=bos_1112))

    print("\n--- tick_buffer on best risk×lb ---")
    for tb in [0, 1, 3]:
        rows.append(bench(f"risk=0.40% lb=14 tb={tb}",
                          {"sl_lookback": 14, "tick_buffer": tb}, 0.0040))

    print("\n--- max_contracts cap ---")
    for mc in [5, 8, 10, 12, 15]:
        rows.append(bench(f"risk=0.40% lb=14 max={mc}",
                          {"sl_lookback": 14}, 0.0040, max_contracts=mc))

    print("\n--- ✅ WR>=50% AND DD<=2500 (sorted by PnL desc) ---")
    good = [r for r in rows if r["win_rate"] >= 50.0 and r["max_dd_$"] <= 2500.0]
    good.sort(key=lambda r: r["net_pnl"], reverse=True)
    if good:
        for r in good[:15]:
            print(f"  ✅ {r['label']:<54s} WR={r['win_rate']:.1f}%  "
                  f"DD=${r['max_dd_$']:,.0f}  PnL=${r['net_pnl']:,.0f}  N={r['trades']}")
    else:
        print("  (none)")
        print("\n--- Top 6 closest at WR>=50% ---")
        close = [r for r in rows if r["win_rate"] >= 50.0]
        close.sort(key=lambda r: r["max_dd_$"])
        for r in close[:6]:
            print(f"  ❌ {r['label']:<54s} WR={r['win_rate']:.1f}%  "
                  f"DD=${r['max_dd_$']:,.0f} (+{r['max_dd_$']-2500:.0f})  PnL=${r['net_pnl']:,.0f}")


if __name__ == "__main__":
    main()
