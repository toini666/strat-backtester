"""Phase 6 — Hour/dow bucket analysis on the V4 baseline trade tape.

Uses the V4 baseline run (same as Phase 1) and bucketizes by entry hour and
day-of-week to identify candidate blackout windows or anomalous time slots.

This is a single backtest + analysis — no sweep here.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from scripts.goals._shared.analysis import (
    bucket_by_dow,
    bucket_by_hour,
    print_dow_table,
    print_hour_table,
)
from scripts.goals._shared.engine_settings import make_engine_settings
from scripts.goals._shared.harness import run_backtest, summarize, fmt_summary

from _campaign import (
    BASELINE_ACTIVE_BLACKOUTS,
    BASELINE_V4_PARAMS,
    END,
    INITIAL_EQUITY,
    INTERVAL,
    MAX_CONTRACTS,
    RISK_PER_TRADE,
    START,
    STRATEGY,
    SYMBOL,
)


def main() -> int:
    print("=" * 100)
    print(f"PHASE 6 — Hour / DOW analysis  |  TF={INTERVAL}  baseline = V3-migrated V4")
    print("=" * 100)

    engine = make_engine_settings(STRATEGY, extra_active_windows=BASELINE_ACTIVE_BLACKOUTS)
    res = run_backtest(
        strategy_name=STRATEGY,
        symbol=SYMBOL,
        interval=INTERVAL,
        start=START,
        end=END,
        strategy_params=BASELINE_V4_PARAMS,
        initial_equity=INITIAL_EQUITY,
        risk_per_trade=RISK_PER_TRADE,
        max_contracts=MAX_CONTRACTS,
        engine_settings=engine,
    )
    s = summarize(res)
    print(f"\nBaseline: {fmt_summary(s)}\n")

    print("\n--- BY ENTRY HOUR (Brussels) ---")
    by_h = bucket_by_hour(res["trades"])
    print_hour_table(by_h)

    print("\n--- BY DAY OF WEEK ---")
    by_d = bucket_by_dow(res["trades"])
    print_dow_table(by_d)

    # Surface candidates: hours with negative total OR avg < 0
    print("\n--- CANDIDATE BLACKOUT HOURS (total < 0 OR avg < -10$) ---")
    candidates = sorted(
        (h for h, v in by_h.items() if v["total"] < 0 or v["avg"] < -10),
        key=lambda h: by_h[h]["total"],
    )
    if not candidates:
        print("  (none — every hour is net positive)")
    else:
        for h in candidates:
            v = by_h[h]
            print(f"  H={h:02d}  n={v['n']:>4}  total=${v['total']:>+8,.0f}  "
                  f"avg=${v['avg']:>+7,.0f}  WR={v['win_rate']:.0f}%")

    print("\n--- HIGH-PNL ANOMALIES (top-3 hours by total) ---")
    top = sorted(by_h.items(), key=lambda kv: -kv[1]["total"])[:3]
    for h, v in top:
        print(f"  H={h:02d}  n={v['n']:>4}  total=${v['total']:>+8,.0f}  "
              f"avg=${v['avg']:>+7,.0f}  WR={v['win_rate']:.0f}%")
    return 0


if __name__ == "__main__":
    sys.exit(main())
