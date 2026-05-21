"""Phase 5 — Filter interactions.

Known dead: hw_level (don't sweep), hw_extreme_filter_on=True catastrophic.
Known good: sig_extreme=15 (V1 default for MGC).

Test:
  - sig_extreme ∈ {10, 12, 15, 20, 25, 30, 40} (with filter ON)
  - hw_extreme ∈ {10, 12, 15, 18, 22, 25} with hw_extreme_filter_on=True
    (re-verify catastrophic — may have changed with other lever shifts)
  - delta_off_mode ∈ {"both", "long_only", "short_only"}
  - cloud_zero_filter_on True/False
  - signal_length ∈ {2, 3, 4, 5, 6}
  - mf_smooth ∈ {3, 4, 5, 6, 7, 8, 10}

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
    print(f"PHASE 5 — Filter interactions @ sl_max={ANCHOR_SL_MAX} r={ANCHOR_RISK*100:.3f}%")
    print("=" * 110)

    base = dict(BASELINE_PARAMS)
    base["sl_max_points"] = ANCHOR_SL_MAX

    print("\n--- 5A: sig_extreme sweep ---")
    for se in [10, 12, 15, 18, 20, 25, 30, 40]:
        p = dict(base)
        p["sig_extreme"] = float(se)
        run(f"sig_extreme={se}", p)

    print("\n--- 5B: signal_length × mf_smooth ---")
    for sl in [2, 3, 4, 5, 6]:
        for mfs in [4, 5, 6, 7, 8]:
            p = dict(base)
            p["signal_length"] = sl
            p["mf_smooth"] = mfs
            run(f"signal_length={sl} mf_smooth={mfs}", p)

    print("\n--- 5C: delta_off_mode ---")
    for dom in ["both", "long_only", "short_only", "none"]:
        p = dict(base)
        p["delta_off_mode"] = dom
        run(f"delta_off_mode={dom}", p)

    print("\n--- 5D: signal_type ---")
    for st in ["SMA", "EMA", "WMA"]:
        p = dict(base)
        p["signal_type"] = st
        run(f"signal_type={st}", p)

    return 0


if __name__ == "__main__":
    sys.exit(main())
