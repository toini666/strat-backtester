"""Sweep 05 — Hour-of-day and day-of-week analysis on BASE_V2.

Bucketize active trades by entry hour and DOW. Identify toxic hours that are
candidates for blackout in sweep 06.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from _campaign import (
    DEFAULT_RISK,
    END,
    INITIAL_EQUITY,
    MAX_CONTRACTS,
    START,
    STRATEGY,
    SYMBOL,
)

from scripts.goals._shared.analysis import (
    bucket_by_dow,
    bucket_by_hour,
    print_dow_table,
    print_hour_table,
)
from scripts.goals._shared.harness import run_backtest, summarize, fmt_summary


TF = "7m"
BASE_V2 = {
    "delta_ext_on": True,
    "cloud_zero_on": True,
    "sig_extreme_on": True,
    "mf_smooth": 3,
    "cooldown_bars": 5,
    "max_candle_pct": 0.7,
}


def main():
    print(f"=== Sweep 05 — hour/dow analysis — {STRATEGY} / {SYMBOL} / {TF} ===")
    print(f"    BASE_V2 = {BASE_V2}")
    print()

    r = run_backtest(
        strategy_name=STRATEGY, symbol=SYMBOL, interval=TF,
        start=START, end=END, strategy_params=BASE_V2,
        initial_equity=INITIAL_EQUITY, risk_per_trade=DEFAULT_RISK,
        max_contracts=MAX_CONTRACTS,
    )
    s = summarize(r)
    print(fmt_summary(s))

    by_hour = bucket_by_hour(r["trades"])
    by_dow = bucket_by_dow(r["trades"])

    print("\n--- By hour ---")
    print_hour_table(by_hour)
    print("\n--- By day-of-week ---")
    print_dow_table(by_dow)

    # Identify toxic hours: total PnL < -$1000 OR avg < -$50 with n>=20
    print("\n--- Toxic hours (total < -$1000 OR (avg<-50 AND n>=20)) ---")
    toxic = []
    for h, d in sorted(by_hour.items()):
        if d["total"] < -1000 or (d["avg"] < -50 and d["n"] >= 20):
            toxic.append(h)
            print(f"  H={h:02d}  n={d['n']:>4} total=${d['total']:>10,.0f} "
                  f"avg=${d['avg']:>7,.0f} WR={d['win_rate']:>5.1f}%")

    print(f"\n  → Candidate blackout hours: {toxic}")

    out = Path(__file__).resolve().parents[1] / "logs" / "05_hour_analysis.json"
    out.write_text(json.dumps({
        "summary": s,
        "by_hour": by_hour,
        "by_dow": by_dow,
        "toxic_hours": toxic,
    }, indent=2, default=str))
    print(f"\n[saved] {out}")


if __name__ == "__main__":
    main()
