"""05 — Hour-of-day and day-of-week bucket analysis.

DIAGNOSTIC ONLY. Per the campaign constraint, we do NOT add hourly blackouts.
This sweep simply documents which hours/days are structurally weak so the
final REPORT can explain the strategy's residual exposure.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _campaign as C  # noqa: E402

from scripts.goals._shared.analysis import (  # noqa: E402
    bucket_by_hour, bucket_by_dow, print_hour_table, print_dow_table,
)
from scripts.goals._shared.harness import run_backtest, summarize, fmt_summary  # noqa: E402


TF = "7m"
BASE = dict(C.PREV_WINNER_PARAMS)
BASE["hw_dir_on"] = False


def main():
    print(f"=== 05 HOUR / DOW ANALYSIS — TF={TF} ===\n")
    r = run_backtest(
        strategy_name=C.STRATEGY, symbol=C.SYMBOL, interval=TF,
        start=C.START, end=C.END, strategy_params=BASE,
        initial_equity=C.INITIAL_EQUITY, risk_per_trade=C.DEFAULT_RISK,
        max_contracts=C.MAX_CONTRACTS,
    )
    s = summarize(r)
    print(f"Reference run: {fmt_summary(s)}\n")

    print("\n--- PnL by entry hour (reference Brussels) ---")
    by_hour = bucket_by_hour(r["trades"])
    print_hour_table(by_hour)

    print("\n--- PnL by day of week ---")
    by_dow = bucket_by_dow(r["trades"])
    print_dow_table(by_dow)

    print("\n--- Hours sorted by total PnL ---")
    items = sorted(by_hour.items(), key=lambda x: x[1]["total"])
    for h, d in items:
        flag = "TOXIC" if d["total"] < -1000 else ("WEAK" if d["total"] < 0 else "")
        print(f"H={h:02d}  n={d['n']:>4}  total=${d['total']:>9,.0f}  avg=${d['avg']:>7,.0f}  WR={d['win_rate']:>5.0f}%  {flag}")


if __name__ == "__main__":
    main()
