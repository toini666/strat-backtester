"""Phase 15 - WINNER risk re-squeeze at sl_max_points=80, plus hour buckets recheck.

Two tasks:
  1. Confirm 0.53 % is still the top-of-cell at sl_max_points=80.
  2. Hour-bucket dump on the new winner trade stream to see if any new BO is obvious.
"""

from __future__ import annotations

import sys
from collections import defaultdict
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.goals._shared.harness import bench, run_backtest, summarize, fmt_summary  # noqa: E402
from scripts.goals._shared.analysis import bucket_by_hour, print_hour_table  # noqa: E402
from _anchor import anchor_kwargs  # noqa: E402


def main() -> None:
    print("Phase 15 - WINNER risk re-squeeze + bucket recheck")
    print("=" * 80)

    print("\n--- rr=1.22 risk re-squeeze at sl_max_points=80 ---")
    for r in [50, 51, 52, 53, 54]:
        rp = r / 100
        bench(f"rr=1.22 risk={rp:.2f}%",
              **anchor_kwargs(params_override={"rr_tp": 1.22}, risk=r / 10000.0))

    # Pull final-config trade stream for bucket analysis at risk=0.42 % (DD cells stable across risk)
    print("\n--- Hour buckets on winner trade stream ---")
    res = run_backtest(**anchor_kwargs(params_override={"rr_tp": 1.22}, risk=0.0053))
    s = summarize(res)
    print("Final winner:", fmt_summary(s))
    by_hour = bucket_by_hour(res["trades"])
    print_hour_table(by_hour)

    print("\n--- Half-hour buckets (potential refinements) ---")
    by_hm = defaultdict(list)
    for t in res["trades"]:
        if t.get("excluded", False):
            continue
        ts = pd.to_datetime(t["entry_time"])
        by_hm[(ts.hour, (ts.minute // 30) * 30)].append(t["pnl"])
    for k in sorted(by_hm):
        h, m = k
        pnls = by_hm[k]
        n = len(pnls)
        if n < 8:
            continue
        wr = sum(1 for p in pnls if p > 0) / n * 100
        if wr >= 45 or sum(pnls) >= 0:
            continue
        print(f"H={h:02d}:{m:02d}  n={n:>3}  total=${sum(pnls):>7,.0f}  avg=${sum(pnls)/n:>5,.0f}  WR={wr:>5.0f}%")


if __name__ == "__main__":
    main()
