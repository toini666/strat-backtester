"""Phase 5 — global MGC + MNQ hour-bucket on ALL trades over the period
to find candidate blackouts to extend. Compare DD-episode vs overall.
"""
import pandas as pd
from collections import defaultdict
from _campaign import (
    MGC_PARAMS_BASE, MNQ_PARAMS_BASE,
    run_multi, fmt_multi, INITIAL_EQUITY,
)


def bucket(trades, key="hour"):
    """Bucket trades by hour or date."""
    bk = defaultdict(lambda: {"pnl": 0.0, "n": 0, "wins": 0, "losses": 0})
    for t in trades:
        if t.get("excluded", False):
            continue
        ts = pd.Timestamp(t["entry_time"])
        if ts.tzinfo:
            ts = ts.tz_convert("Europe/Brussels")
        if key == "hour":
            k = ts.hour
        elif key == "date":
            k = str(ts.date())
        else:
            k = ts.dayofweek
        bk[k]["pnl"] += t["pnl"]
        bk[k]["n"] += 1
        if t["pnl"] > 0:
            bk[k]["wins"] += 1
        else:
            bk[k]["losses"] += 1
    return bk


def main():
    # Use Phase 4 winner config: MGC sl_max=80, both at lower risks
    mgc_p = dict(MGC_PARAMS_BASE)
    mgc_p["sl_max_points"] = 80
    s = run_multi(
        mgc_params=mgc_p, mgc_risk=0.0050,
        mnq_params=MNQ_PARAMS_BASE, mnq_risk=0.0030,
    )
    print(f"Anchor: {fmt_multi(s)}")
    print()

    mgc_trades = [t for t in s["_merged"] if t.get("_leg") == "MGC"]
    mnq_trades = [t for t in s["_merged"] if t.get("_leg") == "MNQ"]

    print("=== MGC trades by hour (overall, current blackouts already applied) ===")
    mgc_bh = bucket(mgc_trades, "hour")
    for h in sorted(mgc_bh.keys()):
        st = mgc_bh[h]
        wr = st["wins"] / st["n"] * 100 if st["n"] > 0 else 0
        marker = "  "
        if st["pnl"] < 0:
            marker = "❌"
        elif st["pnl"] < 500:
            marker = "⚠️"
        print(f"  H={h:>2}: pnl=${st['pnl']:+8,.0f}  N={st['n']:>3}  WR={wr:>4.1f}%  {marker}")

    print()
    print("=== MNQ trades by hour ===")
    mnq_bh = bucket(mnq_trades, "hour")
    for h in sorted(mnq_bh.keys()):
        st = mnq_bh[h]
        wr = st["wins"] / st["n"] * 100 if st["n"] > 0 else 0
        marker = "  "
        if st["pnl"] < 0:
            marker = "❌"
        elif st["pnl"] < 500:
            marker = "⚠️"
        print(f"  H={h:>2}: pnl=${st['pnl']:+8,.0f}  N={st['n']:>3}  WR={wr:>4.1f}%  {marker}")

    print()
    print("=== MGC by day-of-week ===")
    mgc_dow = bucket(mgc_trades, "dow")
    days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    for d in sorted(mgc_dow.keys()):
        st = mgc_dow[d]
        wr = st["wins"] / st["n"] * 100 if st["n"] > 0 else 0
        print(f"  {days[d]}: pnl=${st['pnl']:+8,.0f}  N={st['n']:>3}  WR={wr:>4.1f}%")

    print()
    print("=== MNQ by day-of-week ===")
    mnq_dow = bucket(mnq_trades, "dow")
    for d in sorted(mnq_dow.keys()):
        st = mnq_dow[d]
        wr = st["wins"] / st["n"] * 100 if st["n"] > 0 else 0
        print(f"  {days[d]}: pnl=${st['pnl']:+8,.0f}  N={st['n']:>3}  WR={wr:>4.1f}%")


if __name__ == "__main__":
    main()
