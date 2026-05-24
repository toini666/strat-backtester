"""Phase 1 - Hour-of-day and Day-of-week buckets under the v4 WR WINNER.

Goal: find low-WR / high-loss clusters that could be blackouted to free DD headroom.
The v4 winner already blackouts: 7-8, 12-12:30, 12:30-14, 15:30-17, 18-19, 20-21, 22-23:59.
So untouched hours are: 0-7, 8-12 (partially), 14-15:30, 17-18, 19-20, 21-22.
"""

from __future__ import annotations

import sys
from collections import defaultdict
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.goals._shared.harness import run_backtest, summarize, fmt_summary  # noqa: E402
from scripts.goals._shared.analysis import (  # noqa: E402
    bucket_by_hour, bucket_by_dow, print_hour_table, print_dow_table,
)
from _campaign import seed_kwargs  # noqa: E402


def bucket_by_hour_minute_band(trades, minute_step: int = 30):
    """Bucket by (hour, half-hour) to find sub-hour clusters."""
    by_key = defaultdict(list)
    for t in trades:
        if t.get("excluded", False):
            continue
        ts = pd.to_datetime(t["entry_time"])
        bucket = (ts.hour, (ts.minute // minute_step) * minute_step)
        by_key[bucket].append(t["pnl"])
    out = {}
    for k, pnls in by_key.items():
        out[k] = {
            "n": len(pnls),
            "total": sum(pnls),
            "avg": sum(pnls) / len(pnls),
            "win_rate": sum(1 for p in pnls if p > 0) / len(pnls) * 100,
        }
    return out


def main() -> None:
    print("Phase 1 - Hour & DOW buckets under v4 WR WINNER")
    print("=" * 80)
    result = run_backtest(**seed_kwargs())
    summary = summarize(result)
    print("Anchor:", fmt_summary(summary))
    print()
    trades = result["trades"]

    print("--- Hour-of-day buckets ---")
    by_hour = bucket_by_hour(trades)
    print_hour_table(by_hour)
    print()

    print("--- Day-of-week buckets ---")
    by_dow = bucket_by_dow(trades)
    print_dow_table(by_dow)
    print()

    print("--- Half-hour buckets (only unblackouted hours of interest) ---")
    by_hm = bucket_by_hour_minute_band(trades, minute_step=30)
    interest_hours = {0, 1, 2, 3, 4, 5, 6, 8, 9, 10, 11, 14, 15, 17, 19, 21}
    print(f"{'Bucket':<10}{'n':>5}{'total':>12}{'avg':>10}{'WR':>8}")
    for k in sorted(by_hm):
        h, m = k
        if h not in interest_hours:
            continue
        d = by_hm[k]
        print(f"H={h:02d}:{m:02d}  {d['n']:>5}  ${d['total']:>10,.0f}  ${d['avg']:>7,.0f}  {d['win_rate']:>5.0f}%")
    print()

    print("--- Losing days (worst 10) ---")
    by_day = defaultdict(list)
    for t in trades:
        if t.get("excluded", False):
            continue
        ts = pd.to_datetime(t["entry_time"]).date()
        by_day[ts].append(t["pnl"])
    daily = sorted(
        ((d, sum(p), len(p), sum(1 for x in p if x > 0) / len(p) * 100)
         for d, p in by_day.items()),
        key=lambda x: x[1],
    )
    print(f"{'Date':<12}{'PnL':>10}{'N':>5}{'WR':>8}")
    for d, total, n, wr in daily[:10]:
        print(f"{str(d):<12}  ${total:>7,.0f}  {n:>4}  {wr:>5.0f}%")


if __name__ == "__main__":
    main()
