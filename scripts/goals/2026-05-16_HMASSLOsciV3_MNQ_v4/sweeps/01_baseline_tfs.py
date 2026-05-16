"""01 — Baseline replay (1 sim) + hour/DOW analysis (1 sim, same run).

Replays the v3 winner with the v4 harness (UI defaults for HMASSLOsciV3 → only
22:00-23:59 blackout active). Confirms the baseline reproduces:
  - PnL ≈ $35,472 / DD ≈ $2,491 / N=1405 / WR=43.8% / PF=1.41
Then bucketizes trades by hour and DOW to feed sweep 02.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _campaign as C  # noqa: E402

from scripts.goals._shared.harness import run_backtest, summarize, fmt_summary  # noqa: E402
from scripts.goals._shared.analysis import (  # noqa: E402
    bucket_by_hour,
    bucket_by_dow,
    print_hour_table,
    print_dow_table,
)


def main():
    print(f"=== 01 BASELINE REPLAY — TF={C.TF} ===\n")

    result = run_backtest(
        strategy_name=C.STRATEGY,
        symbol=C.SYMBOL,
        interval=C.TF,
        start=C.START,
        end=C.END,
        strategy_params=dict(C.V3_WINNER_PARAMS),
        initial_equity=C.INITIAL_EQUITY,
        risk_per_trade=C.DEFAULT_RISK,
        max_contracts=C.MAX_CONTRACTS,
    )
    s = summarize(result)
    print(f"BASELINE: {fmt_summary(s)}\n")
    print(f"Expected: PnL≈$35,472 / DD≈$2,491 / N=1405 / WR=43.8% / PF=1.41")

    trades = result["trades"]

    print("\n--- Bucket by Hour (entry hour, Brussels) ---")
    by_h = bucket_by_hour(trades)
    print_hour_table(by_h)

    print("\n--- Bucket by Day-of-Week ---")
    by_d = bucket_by_dow(trades)
    print_dow_table(by_d)

    # Hour ranking (most toxic first)
    print("\n--- Most toxic hours by total $ (negative) ---")
    rank = sorted(by_h.items(), key=lambda kv: kv[1]["total"])
    for h, d in rank[:8]:
        if d["total"] < 0:
            print(f"  H={h:02d}  n={d['n']:>3}  total=${d['total']:>9,.0f}  avg=${d['avg']:>7,.0f}  WR={d['win_rate']:>4.0f}%")

    print("\n--- Most profitable hours by total $ (positive) ---")
    for h, d in rank[-8:][::-1]:
        if d["total"] > 0:
            print(f"  H={h:02d}  n={d['n']:>3}  total=${d['total']:>9,.0f}  avg=${d['avg']:>7,.0f}  WR={d['win_rate']:>4.0f}%")


if __name__ == "__main__":
    main()
