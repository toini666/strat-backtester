"""Sweep 06 — blackout window optimization on the champion.

Seed has 4 active blackouts:  (5-9), (11-13), (14-15), (22-23:59).
Champion: hma_pol_bars=5 + sig_extreme=60 + hw_extreme=35.

Approach:
  1. Hour-of-day analysis on the champion (no extra blackouts beyond 22-23:59)
  2. Test removing each seed blackout
  3. Build new blackout candidates from worst hours
  4. Bundle adjacent worst hours
"""

from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1]))

import pandas as pd  # noqa: E402

from _shared.harness import run_backtest, summarize, fmt_summary  # noqa: E402
from _shared.analysis import bucket_by_hour  # noqa: E402
from _campaign import (  # noqa: E402
    STRATEGY, SYMBOL, INTERVAL, START, END, INITIAL_EQUITY, MAX_CONTRACTS,
    SEED_RISK, SEED_PARAMS, make_engine_settings, seed_engine_settings,
)


CHAMP_PARAMS = dict(SEED_PARAMS)
CHAMP_PARAMS.update({"hma_pol_bars": 5, "sig_extreme": 60, "hw_extreme": 35})


def run(label, active_windows, params=None):
    es = make_engine_settings(active_windows)
    p = dict(CHAMP_PARAMS)
    if params:
        p.update(params)
    res = run_backtest(
        strategy_name=STRATEGY,
        symbol=SYMBOL,
        interval=INTERVAL,
        start=START,
        end=END,
        initial_equity=INITIAL_EQUITY,
        risk_per_trade=SEED_RISK,
        max_contracts=MAX_CONTRACTS,
        strategy_params=p,
        engine_settings=es,
    )
    s = summarize(res)
    s["label"] = label
    s["trades_list"] = res["trades"]
    print(f"{label:<55s} {fmt_summary(s)}")
    return s


SEED_BLACKOUTS = [
    (22, 0, 23, 59),
    (11, 0, 13, 0),
    (14, 0, 15, 0),
    (5, 0, 9, 0),
]


if __name__ == "__main__":
    results = []
    print("=" * 100)
    print("SWEEP 06 — blackout windows on the champion")
    print("=" * 100)

    print()
    print("--- 0. Champion @ seed blackouts (baseline) ---")
    baseline = run("CHAMP @ seed blackouts (4 windows)", SEED_BLACKOUTS)
    results.append(baseline)

    # Minimal blackout: just the post-22 close
    print()
    print("--- 1. Champion @ minimal blackouts (just 22-23:59) ---")
    minimal = run("CHAMP @ minimal (22-23:59 only)", [(22, 0, 23, 59)])
    results.append(minimal)

    # Show hour breakdown of the minimal run
    print()
    print("--- HOUR-OF-DAY breakdown @ minimal ---")
    by_h = bucket_by_hour(minimal["trades_list"])
    print(f"{'Hour':<6}{'n':>5}{'total':>12}{'avg':>10}{'WR':>8}")
    for h in sorted(by_h):
        d = by_h[h]
        marker = " ← NEG" if d["total"] < 0 else ""
        print(f"H={h:02d}  {d['n']:>5}  ${d['total']:>10,.0f}  ${d['avg']:>7,.0f}  {d['win_rate']:>5.0f}%{marker}")

    print()
    print("--- 2. Remove each seed blackout one by one ---")
    for drop in [(5, 0, 9, 0), (11, 0, 13, 0), (14, 0, 15, 0)]:
        wins = [w for w in SEED_BLACKOUTS if w != drop]
        results.append(run(f"DROP {drop}".ljust(55), wins))

    print()
    print("--- 3. Test alternative blackouts: tighter morning ---")
    variants = [
        ("morning 5-8 only", [(22,0,23,59),(11,0,13,0),(14,0,15,0),(5,0,8,0)]),
        ("morning 6-9 only", [(22,0,23,59),(11,0,13,0),(14,0,15,0),(6,0,9,0)]),
        ("morning 7-9 only", [(22,0,23,59),(11,0,13,0),(14,0,15,0),(7,0,9,0)]),
        ("morning 8-9 only", [(22,0,23,59),(11,0,13,0),(14,0,15,0),(8,0,9,0)]),
        ("morning 4-9 wide", [(22,0,23,59),(11,0,13,0),(14,0,15,0),(4,0,9,0)]),
        ("morning 3-9 ultra wide", [(22,0,23,59),(11,0,13,0),(14,0,15,0),(3,0,9,0)]),
        ("morning 0-9 ultra ultra wide", [(22,0,23,59),(11,0,13,0),(14,0,15,0),(0,0,9,0)]),
    ]
    for lab, wins in variants:
        results.append(run(lab.ljust(55), wins))

    print()
    print("--- 4. Tighter midday ---")
    midday = [
        ("midday 11-12 only", [(22,0,23,59),(11,0,12,0),(14,0,15,0),(5,0,9,0)]),
        ("midday 12-13 only", [(22,0,23,59),(12,0,13,0),(14,0,15,0),(5,0,9,0)]),
        ("midday 11-14 wide", [(22,0,23,59),(11,0,14,0),(14,0,15,0),(5,0,9,0)]),
        ("midday 10-13",      [(22,0,23,59),(10,0,13,0),(14,0,15,0),(5,0,9,0)]),
        ("midday 11-15 super wide", [(22,0,23,59),(11,0,15,0),(5,0,9,0)]),
    ]
    for lab, wins in midday:
        results.append(run(lab.ljust(55), wins))

    print()
    print("--- 5. Tighter / wider 14-15 ---")
    afternoon = [
        ("14h30-15h tight", [(22,0,23,59),(11,0,13,0),(14,30,15,0),(5,0,9,0)]),
        ("14-15h30",        [(22,0,23,59),(11,0,13,0),(14,0,15,30),(5,0,9,0)]),
        ("13-15",           [(22,0,23,59),(11,0,13,0),(13,0,15,0),(5,0,9,0)]),  # bug-prone but ok
        ("DROP 14-15",      [(22,0,23,59),(11,0,13,0),(5,0,9,0)]),
        ("14-16",           [(22,0,23,59),(11,0,13,0),(14,0,16,0),(5,0,9,0)]),
    ]
    for lab, wins in afternoon:
        results.append(run(lab.ljust(55), wins))

    print()
    print("=" * 100)
    print("TOP-15 by PnL")
    print("=" * 100)
    for r in sorted(results, key=lambda x: -x["net_pnl"])[:15]:
        print(f"  {r['label']:<55s}  PnL=${r['net_pnl']:>9,.0f} | DD=${r['max_dd_$']:>6,.0f} | N={r['trades']}")

    print()
    print("STRICT PARETO  (PnL >= baseline AND DD < baseline)")
    for r in results[1:]:
        if r["net_pnl"] >= baseline["net_pnl"] and r["max_dd_$"] < baseline["max_dd_$"]:
            print(f"  ✓ {r['label']:<55s}  PnL=${r['net_pnl']:>9,.0f} ({r['net_pnl']-baseline['net_pnl']:+,.0f}) | "
                  f"DD=${r['max_dd_$']:>6,.0f} ({r['max_dd_$']-baseline['max_dd_$']:+,.0f})")
