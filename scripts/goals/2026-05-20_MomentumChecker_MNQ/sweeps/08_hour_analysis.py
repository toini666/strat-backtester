"""Phase 8 — Hour-of-day / day-of-week bucketing on the Phase 6 winner.

Aim: identify worst-PnL hours/days to feed blackout sweep.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from scripts.goals._shared.analysis import bucket_by_hour, bucket_by_dow, print_hour_table, print_dow_table
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
    "min_gap": 9,
    "rr_tp": 2.5,
    "tick_buffer": 0,
    "hw_extreme_filter_on": True,
    "rob_on": False,
    "hw_extreme": 20.0,
    "mf_smooth": 5,
    "st_atr": 14,
    "ema_sec_len": 20,
    "amp_mult": 2.5,
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
    print(f"PHASE 8 — Hour & DoW bucketing on Phase 6 winner")
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
