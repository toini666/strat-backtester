"""Phase 2 — Risk geometry sweeps at the best Phase 1 anchor.

Reads the best sl_max from Phase 1 (or falls back to seed=100), then
sweeps:
  - be_at_rr × rr_tp (joint, 4×4 = 16 sims)
  - sl_lookback × tick_buffer (5×3 = 15 sims)
  - Combined deltas (~5 sims)

~36 sims.
"""

from __future__ import annotations

import sys
import time
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

# anchor params: defaults to seed; user overrides via env if needed
import os
ANCHOR_SL_MAX = float(os.environ.get("ANCHOR_SL_MAX", 100.0))
ANCHOR_RISK   = float(os.environ.get("ANCHOR_RISK", RISK_PER_TRADE))


def run(label, params, risk):
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
    print(f"PHASE 2 — Risk geometry @ sl_max={ANCHOR_SL_MAX} risk={ANCHOR_RISK*100:.3f}%")
    print("=" * 110)

    base = dict(BASELINE_PARAMS)
    base["sl_max_points"] = ANCHOR_SL_MAX

    print("\n--- 2A: be_at_rr × rr_tp joint ---")
    for be in [0.0, 1.0, 1.5, 2.0, 2.5, 3.0]:
        for rr in [2.0, 2.5, 3.0, 3.5]:
            p = dict(base)
            p["be_at_rr"] = be
            p["rr_tp"] = rr
            run(f"be={be:>3.1f} rr_tp={rr:>3.1f}", p, ANCHOR_RISK)

    print("\n--- 2B: sl_lookback × tick_buffer ---")
    for sll in [5, 10, 15, 20, 25]:
        for tb in [1, 2, 3, 4]:
            p = dict(base)
            p["sl_lookback"] = sll
            p["tick_buffer"] = tb
            run(f"sl_lookback={sll:>2} tb={tb}", p, ANCHOR_RISK)

    return 0


if __name__ == "__main__":
    sys.exit(main())
