"""Phase 3 — Thresholds × min_gap × max_candle_pct joint.

Prior MGC v1 found min_gap=8 optimal and thresholds had no effect at
uniform pts=1. Test other thresholds in case point-weight phase finds
non-uniform pts that change the threshold sensitivity.

~36 sims.
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
    print(f"PHASE 3 — Thresholds × min_gap × max_candle_pct  @ sl_max={ANCHOR_SL_MAX} r={ANCHOR_RISK*100:.3f}%")
    print("=" * 110)

    base = dict(BASELINE_PARAMS)
    base["sl_max_points"] = ANCHOR_SL_MAX

    print("\n--- 3A: thresholds (long × short) at min_gap=8 ---")
    for lt in [4, 5, 6, 7]:
        for st in [4, 5, 6, 7]:
            p = dict(base)
            p["long_threshold"] = lt
            p["short_threshold"] = st
            run(f"lt={lt} st={st}", p)

    print("\n--- 3B: min_gap sweep ---")
    for g in [6, 7, 8, 9, 10, 11, 12]:
        p = dict(base)
        p["min_gap"] = g
        run(f"min_gap={g}", p)

    print("\n--- 3C: max_candle_pct ---")
    for mcp in [0.20, 0.25, 0.30, 0.35, 0.40, 0.50, 1.0]:
        p = dict(base)
        p["max_candle_pct"] = mcp
        run(f"max_candle_pct={mcp}", p)

    return 0


if __name__ == "__main__":
    sys.exit(main())
