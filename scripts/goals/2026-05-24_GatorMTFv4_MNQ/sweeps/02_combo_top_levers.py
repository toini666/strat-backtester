"""Sweep 2 — combine the top PnL/DD levers from sweep 1.

Levers:
  final_rr  ∈ {1.5, 1.75, 2.0, 2.5}    (PnL up massively)
  cooldown  ∈ {14, 30, 60, 90, 120}    (DD down massively)
  amp_mult  ∈ {1.0, 1.5, 2.0}          (DD down at small amp)

3 × 4 × 5 = 60 sims.
"""

from __future__ import annotations

import sys
from itertools import product
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.goals._shared.harness import run_backtest, summarize, fmt_summary
from scripts.goals._shared.engine_settings import ui_default_engine_settings
from sweeps._campaign import (
    SEED_PARAMS, SEED_RISK, SEED_AUTO_CLOSE, SEED_BLACKOUTS,
    START, END, SYMBOL, INTERVAL, STRATEGY,
    INITIAL_EQUITY, MAX_CONTRACTS,
)


def _engine():
    es = ui_default_engine_settings(STRATEGY)
    for w in es.blackout_windows:
        w.active = (w.start_hour, w.start_minute, w.end_hour, w.end_minute) in [
            (sh, sm, eh, em) for sh, sm, eh, em in SEED_BLACKOUTS
        ]
    es.auto_close_hour, es.auto_close_minute = SEED_AUTO_CLOSE
    return es


def run_one(label, **overrides):
    params = dict(SEED_PARAMS)
    params.update(overrides)
    r = run_backtest(
        strategy_name=STRATEGY, symbol=SYMBOL, interval=INTERVAL,
        start=START, end=END,
        strategy_params=params,
        initial_equity=INITIAL_EQUITY, risk_per_trade=SEED_RISK,
        max_contracts=MAX_CONTRACTS,
        engine_settings=_engine(),
    )
    s = summarize(r)
    print(f"{label:<55s} {fmt_summary(s)}")
    return s


def main():
    print("=" * 90)
    print("SWEEP 2 — final_rr × cooldown × amp_mult")
    print("=" * 90)

    rrs = [1.5, 1.75, 2.0, 2.5]
    cools = [14, 30, 60, 90, 120]
    amps = [1.0, 1.5, 2.0]

    results = []
    for rr, cd, amp in product(rrs, cools, amps):
        label = f"rr={rr} cd={cd:3d} amp={amp}"
        s = run_one(label, final_rr=rr, cooldown_bars=cd, amp_mult=amp)
        s["rr"] = rr; s["cd"] = cd; s["amp"] = amp
        results.append((label, s))

    print()
    print("=" * 90)
    print("ALL RESULTS — ranked by PnL among DD ≤ $2,500")
    print("=" * 90)
    ok = [(l, s) for l, s in results if s["max_dd_$"] <= 2500.0]
    ok.sort(key=lambda x: -x[1]["net_pnl"])
    for l, s in ok[:30]:
        print(f"  {l:<50s} {fmt_summary(s)}")

    print()
    print("DD ≤ $5,000 (intermediate target — top 20 by PnL)")
    sub5k = [(l, s) for l, s in results if s["max_dd_$"] <= 5000.0]
    sub5k.sort(key=lambda x: -x[1]["net_pnl"])
    for l, s in sub5k[:20]:
        print(f"  {l:<50s} {fmt_summary(s)}")

    print()
    print("BEST PnL (DD unconstrained — top 15)")
    by_pnl = sorted(results, key=lambda x: -x[1]["net_pnl"])
    for l, s in by_pnl[:15]:
        print(f"  {l:<50s} {fmt_summary(s)}")

    print()
    print("BEST DD (top 15)")
    by_dd = sorted(results, key=lambda x: x[1]["max_dd_$"])
    for l, s in by_dd[:15]:
        print(f"  {l:<50s} {fmt_summary(s)}")


if __name__ == "__main__":
    main()
