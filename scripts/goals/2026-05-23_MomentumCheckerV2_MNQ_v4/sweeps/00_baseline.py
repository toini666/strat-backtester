"""Baseline reproduction of the user-provided BEST-MNQ MCV2 7m preset.

Reports the seed metrics + the new win/SL/BE breakdown + recomputes the
exact $ DD (the saved preset only stored % DD). Also dumps an hour-of-day
bucket and a SIG-distribution-on-losers histogram to validate user
hypotheses (low-|sig| trades dominate losses; SLs are too wide).
"""
from __future__ import annotations

import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from scripts.goals._shared.harness import bench, run_backtest, summarize, fmt_summary
from scripts.goals._shared.analysis import bucket_by_hour, print_hour_table
from sweeps._campaign import (
    END,
    INITIAL_EQUITY,
    INTERVAL,
    MAX_CONTRACTS,
    SEED_PARAMS,
    SEED_RISK,
    START,
    STRATEGY,
    SYMBOL,
    make_engine_settings,
)


def run_seed():
    return run_backtest(
        strategy_name=STRATEGY,
        symbol=SYMBOL,
        interval=INTERVAL,
        start=START,
        end=END,
        strategy_params=SEED_PARAMS,
        initial_equity=INITIAL_EQUITY,
        risk_per_trade=SEED_RISK,
        max_contracts=MAX_CONTRACTS,
        engine_settings=make_engine_settings(),
    )


def status_breakdown(trades):
    active = [t for t in trades if not t.get("excluded", False)]
    by_status = Counter(t.get("status", "?") for t in active)
    pnl_by_status = defaultdict(float)
    n_by_status = defaultdict(int)
    pos_by_status = defaultdict(int)
    for t in active:
        s = t.get("status", "?")
        pnl_by_status[s] += t["pnl"]
        n_by_status[s] += 1
        if t["pnl"] > 0:
            pos_by_status[s] += 1
    print("\nStatus breakdown (active trades):")
    print(f"{'Status':<25} {'N':>5} {'WinN':>5} {'WR%':>6} {'NetPnL':>10} {'AvgPnL':>8}")
    for s, n in by_status.most_common():
        wr = (pos_by_status[s] / n * 100) if n else 0
        avg = pnl_by_status[s] / n if n else 0
        print(f"{s:<25} {n:>5} {pos_by_status[s]:>5} {wr:>5.1f}% {pnl_by_status[s]:>10.0f} {avg:>8.0f}")


def hour_table(trades):
    print("\nHour-of-day buckets (entry hour, Brussels ref):")
    print_hour_table(bucket_by_hour(trades))


def sig_on_losers(trades):
    """Group losing trades' entry hour and pnl. SIG values not on trade — would
    need the debug_frame to correlate. Skip if unavailable here; we just
    report SL-vs-non-SL losers per hour.
    """
    active = [t for t in trades if not t.get("excluded", False)]
    losers = [t for t in active if t["pnl"] <= 0]
    wins = [t for t in active if t["pnl"] > 0]
    print(f"\nLosing/winning split:")
    print(f"  winners:   {len(wins):>4}   (sum ${sum(t['pnl'] for t in wins):>9,.0f})")
    print(f"  losers:    {len(losers):>4}   (sum ${sum(t['pnl'] for t in losers):>9,.0f})")
    sl_losers = [t for t in losers if t.get("status") in ("Stop Loss", "Trailing SL")]
    be_like = [t for t in losers if abs(t["exit_price"] - t["entry_price"]) <= 0.5]  # 2 ticks MNQ
    other = [t for t in losers if t not in sl_losers and t not in be_like]
    print(f"  SL losers:        {len(sl_losers):>4}  avg=${(sum(t['pnl'] for t in sl_losers)/max(1,len(sl_losers))):>7,.0f}")
    print(f"  BE-like (<=2tk):  {len(be_like):>4}  avg=${(sum(t['pnl'] for t in be_like)/max(1,len(be_like))):>7,.0f}")
    print(f"  other losers:     {len(other):>4}  avg=${(sum(t['pnl'] for t in other)/max(1,len(other))):>7,.0f}")


def main():
    print("=" * 100)
    print(f"BASELINE — {STRATEGY} | {SYMBOL} {INTERVAL} | {START} → {END}")
    print(f"  risk={SEED_RISK*100:.2f}% max_contracts={MAX_CONTRACTS}")
    print("=" * 100)

    result = run_seed()
    s = summarize(result)
    s["label"] = "SEED (BEST-MNQ MCV2 7m)"
    print(f"\n{s['label']:<60} {fmt_summary(s)}")
    print(f"\n  Raw metrics dict:")
    for k, v in result["metrics"].items():
        print(f"    {k:<25} = {v}")

    status_breakdown(result["trades"])
    hour_table(result["trades"])
    sig_on_losers(result["trades"])

    # Sanity sample: 10 lowest-|pnl| losers — are they "in/out at same price"?
    active = [t for t in result["trades"] if not t.get("excluded", False)]
    losers = sorted([t for t in active if t["pnl"] < 0], key=lambda t: t["pnl"], reverse=True)[:10]
    print("\nLowest-|pnl| losers (10):")
    print(f"{'pnl':>8} {'entry':>10} {'exit':>10} {'Δprice':>8} {'size':>5} {'status':<22} {'side':<6}")
    for t in losers:
        dp = t["exit_price"] - t["entry_price"]
        print(f"{t['pnl']:>8.1f} {t['entry_price']:>10.2f} {t['exit_price']:>10.2f} "
              f"{dp:>+8.3f} {t['size']:>5.0f} {t.get('status', '?'):<22} {t['side']:<6}")


if __name__ == "__main__":
    main()
