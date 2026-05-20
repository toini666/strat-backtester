"""Phase 7 — Hour and day-of-week bucketing on Phase 6 winner.

Phase 6 winner config: PnL=$46,100, DD=$2,712. Still $212 over DD budget.
Goal: identify which hours/days bleed the most so a targeted blackout removes
losing slices without giving up too much PnL.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from scripts.goals._shared.analysis import bucket_by_hour, bucket_by_dow, print_dow_table
from scripts.goals._shared.harness import run_backtest, summarize, fmt_summary

from _campaign import (
    BASELINE_PARAMS,
    END,
    INITIAL_EQUITY,
    INTERVAL,
    MAX_CONTRACTS,
    RISK_PER_TRADE,
    START,
    STRATEGY,
    SYMBOL,
    baseline_engine,
)


WINNER = dict(BASELINE_PARAMS)
WINNER.update({
    "min_gap": 8,
    "sl_lookback": 15,
    "rr_tp": 3.0,
    "sl_max_points": 50.0,
    "ut_on": False,
    "sig_extreme_filter_on": True,
    "hw_extreme": 15.0,
    "stc_length": 10,
    "stc_fast_len": 32,
})


def main() -> int:
    r = run_backtest(
        strategy_name=STRATEGY,
        symbol=SYMBOL,
        interval=INTERVAL,
        start=START,
        end=END,
        strategy_params=WINNER,
        initial_equity=INITIAL_EQUITY,
        risk_per_trade=RISK_PER_TRADE,
        max_contracts=MAX_CONTRACTS,
        engine_settings=baseline_engine(),
    )
    s = summarize(r)
    print("=" * 100)
    print(f"PHASE 7 — Hour & DoW bucketing on Phase 6 winner")
    print("=" * 100)
    print(f"Winner: {fmt_summary(s)}")
    print()

    trades = r["trades"]
    by_hour = bucket_by_hour(trades)
    by_dow = bucket_by_dow(trades)

    print("Hours sorted by total PnL (worst first):")
    print(f"  {'H':<5}{'n':>5}{'total':>13}{'avg':>10}{'WR':>8}")
    for h, d in sorted(by_hour.items(), key=lambda x: x[1]["total"]):
        flag = " ← BAD" if d["total"] < 0 else ""
        print(f"  H={h:02d}{d['n']:>5}  ${d['total']:>10,.0f}  ${d['avg']:>7,.0f}  {d['win_rate']:>5.0f}%{flag}")

    print()
    print("Hours sorted by total PnL (best first):")
    print(f"  {'H':<5}{'n':>5}{'total':>13}{'avg':>10}{'WR':>8}")
    for h, d in sorted(by_hour.items(), key=lambda x: -x[1]["total"]):
        print(f"  H={h:02d}{d['n']:>5}  ${d['total']:>10,.0f}  ${d['avg']:>7,.0f}  {d['win_rate']:>5.0f}%")

    print()
    print("Day-of-week table:")
    print_dow_table(by_dow)

    return 0


if __name__ == "__main__":
    sys.exit(main())
