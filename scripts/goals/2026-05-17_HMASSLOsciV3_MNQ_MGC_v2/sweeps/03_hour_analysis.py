"""Step 3 — bucket trades by hour and day-of-week for each leg.

Goal: identify hours that systematically drag PnL or contribute to DD windows.
"""
from __future__ import annotations

import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _campaign import run_multi, MNQ_BASE_RISK, MGC_BASE_RISK  # noqa: E402


def _hour(t):
    if isinstance(t, datetime):
        return t.hour
    return int(str(t)[11:13])


def _dow(t):
    if isinstance(t, datetime):
        return t.weekday()
    return datetime.fromisoformat(str(t).replace("Z", "+00:00")).weekday()


def bucket_hour(trades, source):
    by_h = defaultdict(lambda: {"n": 0, "pnl": 0.0})
    for t in trades:
        if t.get("source") != source or t.get("excluded"):
            continue
        h = _hour(t["entry_time"])
        by_h[h]["n"] += 1
        by_h[h]["pnl"] += t["pnl"]
    return dict(by_h)


def bucket_dow(trades, source):
    by_d = defaultdict(lambda: {"n": 0, "pnl": 0.0})
    for t in trades:
        if t.get("source") != source or t.get("excluded"):
            continue
        d = _dow(t["entry_time"])
        by_d[d]["n"] += 1
        by_d[d]["pnl"] += t["pnl"]
    return dict(by_d)


def print_h_table(title, b):
    print(f"\n{title}")
    print(f"{'H':>3} {'N':>5} {'PnL':>10} {'avg':>8}")
    total = sum(v["pnl"] for v in b.values())
    print(f"{'tot':>3} {sum(v['n'] for v in b.values()):>5} {total:>10,.0f}")
    for h in range(24):
        if h in b:
            n = b[h]["n"]
            p = b[h]["pnl"]
            avg = p / n if n else 0.0
            mark = " <- LOSER" if p < -200 else (" *" if p > 2500 else "")
            print(f"{h:>3} {n:>5} {p:>10,.0f} {avg:>8.1f}{mark}")


def print_dow_table(title, b):
    days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    print(f"\n{title}")
    print(f"{'D':>4} {'N':>5} {'PnL':>10} {'avg':>8}")
    for d in range(7):
        if d in b:
            n = b[d]["n"]
            p = b[d]["pnl"]
            avg = p / n if n else 0.0
            print(f"{days[d]:>4} {n:>5} {p:>10,.0f} {avg:>8.1f}")


print("Running baseline with trade list...")
result = run_multi(mnq_risk=MNQ_BASE_RISK, mgc_risk=MGC_BASE_RISK, return_trades=True)
print(f"  Total PnL=${result['net_pnl']:,.0f} DD=${result['max_dd_$']:,.0f}")
print(f"  MNQ trades={result['mnq_trades']} PnL=${result['mnq_pnl']:,.0f}")
print(f"  MGC trades={result['mgc_trades']} PnL=${result['mgc_pnl']:,.0f}")

trades = result["trades_list"]

print_h_table("MNQ — Hour buckets", bucket_hour(trades, "1"))
print_h_table("MGC — Hour buckets", bucket_hour(trades, "2"))
print_dow_table("MNQ — DOW buckets", bucket_dow(trades, "1"))
print_dow_table("MGC — DOW buckets", bucket_dow(trades, "2"))

# DD window walk: find the largest peak-trough on the merged equity.
active = sorted([t for t in trades if not t.get("excluded")], key=lambda t: t["entry_time"])
equity = 50_000.0
peak = 50_000.0
peak_time = None
worst_dd = 0.0
worst_peak_t = None
worst_trough_t = None
cur_peak_t = active[0]["entry_time"] if active else None
for t in active:
    equity += t["pnl"]
    if equity > peak:
        peak = equity
        cur_peak_t = t["entry_time"]
    dd = peak - equity
    if dd > worst_dd:
        worst_dd = dd
        worst_peak_t = cur_peak_t
        worst_trough_t = t["entry_time"]

print("\n=== Worst DD window ===")
print(f"  Peak  : {worst_peak_t}")
print(f"  Trough: {worst_trough_t}")
print(f"  DD$   : ${worst_dd:,.2f}")

# Trades inside that window, source breakdown
if worst_peak_t and worst_trough_t:
    in_win = [t for t in active if worst_peak_t <= t["entry_time"] <= worst_trough_t]
    mnq_w = [t for t in in_win if t.get("source") == "1"]
    mgc_w = [t for t in in_win if t.get("source") == "2"]
    print(f"  Trades in window: {len(in_win)} (MNQ={len(mnq_w)}/MGC={len(mgc_w)})")
    print(f"  MNQ PnL in window: ${sum(t['pnl'] for t in mnq_w):,.0f}")
    print(f"  MGC PnL in window: ${sum(t['pnl'] for t in mgc_w):,.0f}")

    # Hour distribution in window
    mnq_h = defaultdict(lambda: {"n": 0, "pnl": 0.0})
    for t in mnq_w:
        h = _hour(t["entry_time"])
        mnq_h[h]["n"] += 1
        mnq_h[h]["pnl"] += t["pnl"]
    mgc_h = defaultdict(lambda: {"n": 0, "pnl": 0.0})
    for t in mgc_w:
        h = _hour(t["entry_time"])
        mgc_h[h]["n"] += 1
        mgc_h[h]["pnl"] += t["pnl"]
    print_h_table("DD-window MNQ hours", dict(mnq_h))
    print_h_table("DD-window MGC hours", dict(mgc_h))
