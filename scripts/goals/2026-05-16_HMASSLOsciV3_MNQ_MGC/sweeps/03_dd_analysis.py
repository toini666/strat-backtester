"""03 — find when the combined DD peak occurs, and which trades drive it."""
from __future__ import annotations

import sys
from collections import defaultdict
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _campaign import (  # noqa: E402
    DD_BUDGET, INITIAL_EQUITY, MGC_BASE_RISK, MNQ_BASE_RISK, run_multi,
)


def analyze(label: str, scale: float) -> None:
    s = run_multi(
        mnq_risk=MNQ_BASE_RISK * scale,
        mgc_risk=MGC_BASE_RISK * scale,
        return_trades=True,
    )
    trades = s["trades_list"]
    active = sorted([t for t in trades if not t.get("excluded", False)],
                    key=lambda t: t["entry_time"])

    # Walk equity curve & find DD peak window.
    equity = INITIAL_EQUITY
    peak = INITIAL_EQUITY
    peak_time = None
    trough_equity = INITIAL_EQUITY
    trough_time = None
    max_dd = 0.0
    best_peak_time = None
    best_trough_time = None
    cur_peak_time = None
    for t in active:
        equity += t["pnl"]
        exit_t = t.get("exit_execution_time") or t["exit_time"]
        if equity > peak:
            peak = equity
            cur_peak_time = exit_t
        dd = peak - equity
        if dd > max_dd:
            max_dd = dd
            best_peak_time = cur_peak_time
            best_trough_time = exit_t

    print(f"\n=== {label} (scale={scale}) — combined DD analysis")
    print(f"  PnL combined : ${s['net_pnl']:+,.0f}")
    print(f"  Max DD $     : ${s['max_dd_$']:,.0f}")
    print(f"  Peak time    : {best_peak_time}")
    print(f"  Trough time  : {best_trough_time}")

    # Identify the trades during the DD window (from peak_time to trough_time inclusive).
    if best_peak_time and best_trough_time:
        peak_ts = pd.Timestamp(best_peak_time)
        trough_ts = pd.Timestamp(best_trough_time)
        in_window = [t for t in active
                     if peak_ts < pd.Timestamp(t.get("exit_execution_time") or t["exit_time"]) <= trough_ts]
        m_loss = sum(t["pnl"] for t in in_window if t.get("source") == "1")
        g_loss = sum(t["pnl"] for t in in_window if t.get("source") == "2")
        print(f"  DD window N  : {len(in_window)} trades  "
              f"(MNQ {sum(1 for t in in_window if t.get('source')=='1')}, "
              f"MGC {sum(1 for t in in_window if t.get('source')=='2')})")
        print(f"  DD window PnL: MNQ=${m_loss:+,.0f}  MGC=${g_loss:+,.0f}")
        # Days in the DD window
        days = sorted({pd.Timestamp(t.get("exit_execution_time") or t["exit_time"]).date()
                       for t in in_window})
        print(f"  Window days  : {len(days)} ({days[0]} → {days[-1]})")

    # Hour-of-day bucketing per leg (entry hour reference Brussels).
    def hour_bucket(src: str) -> None:
        per_hour = defaultdict(lambda: {"n": 0, "pnl": 0.0, "wins": 0})
        for t in active:
            if t.get("source") != src:
                continue
            ts = pd.Timestamp(t["entry_time"])
            h = ts.hour
            per_hour[h]["n"] += 1
            per_hour[h]["pnl"] += t["pnl"]
            per_hour[h]["wins"] += 1 if t["pnl"] > 0 else 0
        print(f"\n  {'MNQ' if src == '1' else 'MGC'} bucket by hour (entry):")
        print(f"    {'H':>3} {'N':>4} {'PnL':>12} {'avg':>8} {'WR%':>6}")
        for h in sorted(per_hour.keys()):
            d = per_hour[h]
            wr = d["wins"] / d["n"] * 100 if d["n"] else 0
            print(f"    {h:>3} {d['n']:>4} {d['pnl']:>+12,.0f} {d['pnl']/d['n']:>+8,.0f} {wr:>6.1f}")

    hour_bucket("1")
    hour_bucket("2")

    # Worst days for combined
    by_day = defaultdict(float)
    by_day_m = defaultdict(float)
    by_day_g = defaultdict(float)
    for t in active:
        d = pd.Timestamp(t["entry_time"]).date()
        by_day[d] += t["pnl"]
        if t.get("source") == "1":
            by_day_m[d] += t["pnl"]
        else:
            by_day_g[d] += t["pnl"]
    worst_days = sorted(by_day.items(), key=lambda x: x[1])[:15]
    print(f"\n  Worst 15 combined days:")
    print(f"    {'date':<12} {'combined':>10} {'MNQ':>10} {'MGC':>10}")
    for d, p in worst_days:
        print(f"    {str(d):<12} {p:>+10,.0f} {by_day_m[d]:>+10,.0f} {by_day_g[d]:>+10,.0f}")

    # Best days
    best_days = sorted(by_day.items(), key=lambda x: -x[1])[:10]
    print(f"\n  Best 10 combined days:")
    print(f"    {'date':<12} {'combined':>10} {'MNQ':>10} {'MGC':>10}")
    for d, p in best_days:
        print(f"    {str(d):<12} {p:>+10,.0f} {by_day_m[d]:>+10,.0f} {by_day_g[d]:>+10,.0f}")


def main() -> None:
    analyze("baseline (scale=1.0)", 1.0)


if __name__ == "__main__":
    main()
