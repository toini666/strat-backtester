"""Hour-of-day + day-of-week analysis on the best combo so far.

Runs the best combo once, then buckets trades by entry hour to identify
which hours bleed money — guides blackout window choices in sweep 5.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.goals._shared.harness import run_backtest, summarize, fmt_summary
from scripts.goals._shared.engine_settings import ui_default_engine_settings
from scripts.goals._shared.analysis import (
    bucket_by_hour, bucket_by_dow, print_hour_table, print_dow_table,
)
from sweeps._campaign import (
    SEED_PARAMS, SEED_RISK, SEED_AUTO_CLOSE, SEED_BLACKOUTS,
    START, END, SYMBOL, INTERVAL, STRATEGY,
    INITIAL_EQUITY, MAX_CONTRACTS,
)


# From sweep 3 winner: ABCD=1101 (case_c off).
BEST_COMBO = {
    "final_rr": 2.0,
    "cooldown_bars": 90,
    "amp_mult": 1.0,
    "case_c_on": False,
}


def _engine():
    es = ui_default_engine_settings(STRATEGY)
    for w in es.blackout_windows:
        w.active = (w.start_hour, w.start_minute, w.end_hour, w.end_minute) in [
            (sh, sm, eh, em) for sh, sm, eh, em in SEED_BLACKOUTS
        ]
    es.auto_close_hour, es.auto_close_minute = SEED_AUTO_CLOSE
    return es


def main():
    params = dict(SEED_PARAMS)
    params.update(BEST_COMBO)

    r = run_backtest(
        strategy_name=STRATEGY, symbol=SYMBOL, interval=INTERVAL,
        start=START, end=END,
        strategy_params=params,
        initial_equity=INITIAL_EQUITY, risk_per_trade=SEED_RISK,
        max_contracts=MAX_CONTRACTS,
        engine_settings=_engine(),
    )
    s = summarize(r)
    print("BASE COMBO:")
    print(f"  {fmt_summary(s)}")
    print()

    trades = r["trades"]
    print("=" * 60)
    print("HOUR-OF-DAY BUCKETS")
    print("=" * 60)
    by_hour = bucket_by_hour(trades)
    print_hour_table(by_hour)

    # Highlight losers / under-performers
    print()
    print("LOSING HOURS (total < 0):")
    losers = sorted(
        [(h, d) for h, d in by_hour.items() if d["total"] < 0],
        key=lambda x: x[1]["total"],
    )
    for h, d in losers:
        print(f"  H={h:02d}  n={d['n']:>4}  total=${d['total']:>10,.0f}  "
              f"avg=${d['avg']:>7,.0f}  WR={d['win_rate']:>4.0f}%")

    print()
    print("BELOW-AVG HOURS (total < $1000 OR avg < $-5):")
    below = sorted(
        [(h, d) for h, d in by_hour.items()
         if d["total"] < 1000.0 or d["avg"] < -5.0],
        key=lambda x: x[1]["total"],
    )
    for h, d in below:
        print(f"  H={h:02d}  n={d['n']:>4}  total=${d['total']:>10,.0f}  "
              f"avg=${d['avg']:>7,.0f}  WR={d['win_rate']:>4.0f}%")

    print()
    print("=" * 60)
    print("DAY-OF-WEEK BUCKETS")
    print("=" * 60)
    by_dow = bucket_by_dow(trades)
    print_dow_table(by_dow)


if __name__ == "__main__":
    main()
