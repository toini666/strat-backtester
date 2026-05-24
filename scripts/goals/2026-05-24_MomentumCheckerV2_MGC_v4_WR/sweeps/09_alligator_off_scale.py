"""Phase 9 — alligator_on=False breakthrough — scale up trade count.

Phase 8 found: alligator_on=False @ rr=1.25/lb=15 → WR=54.5%, DD=$1,163, PnL=$4,440, N=99.

Trade count too low (99/16mo = ~6/mo). Need to scale.

Levers to tune:
A) Lower long/short_threshold (5 → 4 or 3) to admit more setups.
B) Different rr_tp (since fewer trades, larger TPs might rebalance PnL/WR).
C) Different min_gap.
D) Selective alligator-points: only `pts_alligator=0`, keep `pts_alli_offset` and
   `pts_retest_lips` enabled? Or vice-versa.
"""
from __future__ import annotations
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.goals._shared.harness import run_backtest, summarize, fmt_summary
from _campaign import seed_kwargs


ALLI_OFF = {"alligator_on": False}


def bench(label, params=None, rr=1.25, lb=15):
    p = {"rr_tp": rr, "sl_lookback": lb, "alligator_on": False}
    if params:
        p.update(params)
    kw = seed_kwargs(params=p)
    r = run_backtest(**kw)
    s = summarize(r)
    s["label"] = label
    print(f"{label:<60s} | {fmt_summary(s)}")
    return s


def main():
    print("--- ALLIGATOR-OFF ANCHOR rr=1.25 lb=15 ---")
    a = bench("anchor (alli OFF)")

    print("\n--- A) lower long/short_threshold ---")
    rows = []
    for th in [4, 3, 2]:
        rows.append(bench(f"threshold={th}",
                          params={"long_threshold": th, "short_threshold": th}))

    print("\n--- B) different rr_tp at alli OFF ---")
    for rr in [3.0, 2.5, 2.0, 1.6, 1.55, 1.5, 1.4, 1.3]:
        rows.append(bench(f"rr={rr}", rr=rr))

    print("\n--- C) different sl_lookback at alli OFF ---")
    for lb in [7, 10, 12, 18, 20]:
        rows.append(bench(f"lb={lb}", lb=lb))

    print("\n--- D) Min_gap variations at alli OFF ---")
    for mg in [5, 6, 7, 9, 10]:
        rows.append(bench(f"min_gap={mg}", params={"min_gap": mg}))

    print("\n--- E) Selective alligator points (alli ON, points dropped) ---")
    p_combos = [
        ("alli ON pts_alligator=0", {"alligator_on": True, "pts_alligator": 0}),
        ("alli ON pts_alli_offset=0", {"alligator_on": True, "pts_alli_offset": 0}),
        ("alli ON pts_retest_lips=0", {"alligator_on": True, "pts_retest_lips": 0}),
        ("alli ON only pts_retest_lips", {"alligator_on": True, "pts_alligator": 0, "pts_alli_offset": 0}),
        ("alli ON only pts_alligator", {"alligator_on": True, "pts_alli_offset": 0, "pts_retest_lips": 0}),
    ]
    for label, p in p_combos:
        p2 = dict(p)
        rows.append(bench(label, params=p2))

    print("\n--- F) threshold=3 + low rr_tp combinations ---")
    for rr in [1.55, 1.5, 1.4, 1.3]:
        rows.append(bench(f"th=3 rr={rr}",
                          params={"long_threshold": 3, "short_threshold": 3}, rr=rr))

    print(f"\nANCHOR: PnL=${a['net_pnl']:,.0f}  DD=${a['max_dd_$']:,.0f}  WR={a['win_rate']:.1f}%  N={a['trades']}")

    print("\n--- ✅ WR>=50% AND DD<=2500 (sorted by PnL) ---")
    good = [r for r in rows if r["win_rate"] >= 50.0 and r["max_dd_$"] <= 2500.0]
    good.sort(key=lambda r: r["net_pnl"], reverse=True)
    if good:
        for r in good[:15]:
            print(f"  ✅ {r['label']:<46s} WR={r['win_rate']:.1f}%  "
                  f"DD=${r['max_dd_$']:,.0f}  PnL=${r['net_pnl']:,.0f}  N={r['trades']}")
    else:
        print("  (none)")


if __name__ == "__main__":
    main()
