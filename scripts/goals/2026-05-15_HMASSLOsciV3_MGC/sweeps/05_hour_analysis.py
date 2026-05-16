"""05 — Hour-of-day & day-of-week PnL bucketing on the best base config.

Identifies toxic hours candidate for blackouts.
"""

from __future__ import annotations

import json
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
# Top single-1D winner from sweep 03 (P/DD=6.32). Combining further 1D winners
# proved non-additive (see logs/03b_combo_test.log).
BASE_PARAMS = {
    "hw_range_on": True,
    "hma2_len": 34,
}
RISK = 0.01


def main():
    print(f"=== 05 HOUR / DOW analysis — M7 {BASE_PARAMS} risk={RISK} ===\n", flush=True)
    r = run_backtest(
        strategy_name=C.STRATEGY, symbol=C.SYMBOL,
        interval=TF, start=C.START, end=C.END,
        strategy_params=BASE_PARAMS,
        initial_equity=C.INITIAL_EQUITY,
        risk_per_trade=RISK,
        max_contracts=C.MAX_CONTRACTS,
    )
    s = summarize(r)
    print("Base run:", fmt_summary(s), "\n")

    print("--- Hour-of-day buckets (reference Brussels) ---")
    by_hour = bucket_by_hour(r["trades"])
    print_hour_table(by_hour)

    print("\n--- Day-of-week buckets ---")
    by_dow = bucket_by_dow(r["trades"])
    print_dow_table(by_dow)

    out = Path(__file__).resolve().parents[1] / "logs" / "05_hour_analysis.json"
    out.write_text(json.dumps({"by_hour": by_hour, "by_dow": by_dow}, indent=2, default=str))
    print(f"\n[saved] {out}")


if __name__ == "__main__":
    main()
