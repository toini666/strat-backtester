"""Phase 4 — Point weight combos.

Known dead from prior: pts_hw_value (don't sweep).
MNQ v3 winner: pts_ema_align=2 was key.

Test:
  - pts_ema_align ∈ {0, 1, 2}
  - pts_stc ∈ {0, 1, 2}
  - pts_st ∈ {0, 1, 2}
  - pts_alligator ∈ {0, 1, 2}
  - pts_ut_bot ∈ {0, 1, 2} (note: ut_on=False in seed so 0 expected)
  - pts_hma_break ∈ {0, 1, 2}, pts_hma_slow ∈ {0, 1, 2}
  - cloud/delta/sig_extreme bumps

~40 sims.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

CAMPAIGN_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CAMPAIGN_DIR / "sweeps"))

from scripts.goals._shared.harness import run_backtest, summarize, fmt_summary  # noqa: E402

from _campaign import (  # noqa: E402
    BASELINE_PARAMS, END, INITIAL_EQUITY, INTERVAL, MAX_CONTRACTS,
    RISK_PER_TRADE, START, STRATEGY, SYMBOL, seed_engine,
)

ANCHOR_SL_MAX = float(os.environ.get("ANCHOR_SL_MAX", 100.0))
ANCHOR_RISK   = float(os.environ.get("ANCHOR_RISK", RISK_PER_TRADE))


def run(label, params, risk=ANCHOR_RISK):
    r = run_backtest(
        strategy_name=STRATEGY, symbol=SYMBOL, interval=INTERVAL,
        start=START, end=END,
        initial_equity=INITIAL_EQUITY, risk_per_trade=risk,
        max_contracts=MAX_CONTRACTS,
        engine_settings=seed_engine(),
        strategy_params=params,
    )
    s = summarize(r)
    s["label"] = label
    print(f"{label:<60s} {fmt_summary(s)}")
    return s


def main() -> int:
    print("=" * 110)
    print(f"PHASE 4 — Point weight combos  @ sl_max={ANCHOR_SL_MAX} r={ANCHOR_RISK*100:.3f}%")
    print("=" * 110)

    base = dict(BASELINE_PARAMS)
    base["sl_max_points"] = ANCHOR_SL_MAX

    PTS_AXES = [
        "pts_ema_break", "pts_ema_align",
        "pts_st", "pts_alligator", "pts_alli_offset", "pts_retest_lips",
        "pts_stc",
        "pts_hma_break", "pts_hma_slow",
        "pts_cloud", "pts_delta", "pts_sig_extreme", "pts_hw_sens",
        "pts_hw_extreme",
    ]

    print("\n--- 4A: each pts axis individually to 2 ---")
    for axis in PTS_AXES:
        p = dict(base)
        p[axis] = 2
        run(f"{axis}=2", p)

    print("\n--- 4B: each pts axis individually to 0 (disable) ---")
    for axis in PTS_AXES:
        p = dict(base)
        p[axis] = 0
        run(f"{axis}=0", p)

    print("\n--- 4C: pts_ema_align=2 combos with other +1 bumps ---")
    for axis in ["pts_st", "pts_stc", "pts_alligator", "pts_hma_break", "pts_hma_slow",
                 "pts_cloud", "pts_delta", "pts_sig_extreme"]:
        p = dict(base)
        p["pts_ema_align"] = 2
        p[axis] = 2
        run(f"ema_align=2 + {axis}=2", p)

    return 0


if __name__ == "__main__":
    sys.exit(main())
