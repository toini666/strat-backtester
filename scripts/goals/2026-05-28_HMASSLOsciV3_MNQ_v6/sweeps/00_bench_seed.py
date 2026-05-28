"""Bench the seed preset to confirm reproduction.

Expected (from preset metrics):
  PnL ~$63,143 (126.29% × $50k)
  DD  ~$3,556.76 (4.62%)
  Trades 1070
  Win rate 49.35%
"""

from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1]))  # scripts/goals

from _shared.harness import bench  # noqa: E402
from _campaign import run_seed_kwargs  # noqa: E402


if __name__ == "__main__":
    s = bench("seed (MNQ-PROD HMASSLOsciV3)", **run_seed_kwargs())
    print()
    print(f"DELTA-PnL vs preset.metrics 126.29%×50k=$63,143: ${s['net_pnl'] - 63143:.0f}")
    print(f"DELTA-DD  vs preset.metrics $3,556.76:           ${s['max_dd_$'] - 3556.76:.0f}")
