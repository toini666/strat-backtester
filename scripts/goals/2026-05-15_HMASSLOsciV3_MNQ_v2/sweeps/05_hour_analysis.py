"""05 — Trade-level hour / DOW analysis on the best base config.

Bucketise trades by entry hour and day-of-week.  Spot:
- structurally losing hours → candidates for blackout
- abnormally high-PnL hours → look for bias (DST, single contract …)
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _campaign as C  # noqa: E402

from scripts.goals._shared.analysis import (  # noqa: E402
    bucket_by_dow,
    bucket_by_hour,
    print_dow_table,
    print_hour_table,
)
from scripts.goals._shared.harness import run_backtest, summarize, fmt_summary  # noqa: E402

TF = "7m"
# Step-03 winners combined.
BASE_PARAMS = {
    "cloud_on": True,
    "hma_pol_bars": 0,
    "signal_length": 2,
    "hyper_wave_length": 7,
    "mf_length": 25,
    "ssl_len": 80,
    "entry_window_bars": 3,
}


def main():
    print(f"=== 05 HOUR / DOW ANALYSIS — base = M7 {BASE_PARAMS} ===\n")
    result = run_backtest(
        strategy_name=C.STRATEGY, symbol=C.SYMBOL, interval=TF,
        start=C.START, end=C.END,
        strategy_params=BASE_PARAMS,
        initial_equity=C.INITIAL_EQUITY,
        risk_per_trade=C.DEFAULT_RISK,
        max_contracts=C.MAX_CONTRACTS,
    )
    summary = summarize(result)
    print(f"BASE: {fmt_summary(summary)}\n")

    print("--- Hour of day (entry, reference Brussels) ---")
    by_hour = bucket_by_hour(result["trades"])
    print_hour_table(by_hour)

    print("\n--- Day of week ---")
    by_dow = bucket_by_dow(result["trades"])
    print_dow_table(by_dow)

    print("\n--- Losing hours (total<0) candidates for blackout ---")
    bad = [(h, d) for h, d in by_hour.items() if d["total"] < 0]
    bad.sort(key=lambda x: x[1]["total"])
    for h, d in bad:
        print(f"  H={h:02d}  total=${d['total']:>10,.0f}  avg=${d['avg']:>7,.0f}  n={d['n']}")


if __name__ == "__main__":
    main()
