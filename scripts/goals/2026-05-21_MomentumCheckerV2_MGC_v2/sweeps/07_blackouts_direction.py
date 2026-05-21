"""Phase 7 — Surgical blackouts re-explore + direction restriction.

From Phase 0 diagnostic (minimal engine):
  - Losing hours: H=12 (-$1,298), H=13 (-$615), H=18 (-$525),
                  H=20 (-$939), H=23 (-$2,482)
  - Profitable hours blocked by seed: H=22 (+$2,200), H=14 (+$1,174)
  - Seed already blocks 12:30-14, 18-19, 20-21, 22-23:59

Tests:
  - Tighten blackouts (block H=12 fully, block H=23 only)
  - Add H=01 blackout if any signal of weakness
  - Direction restriction (long-only / short-only / both)

Note for direction restriction: MomentumCheckerV2 doesn't have a built-in
direction flag — we approximate by zeroing the corresponding threshold
to an impossible value (e.g. long_threshold=99 disables longs) OR by
setting long_entries to False at runtime via a post-hook. We'll use the
threshold trick first.

~30 sims.
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
    RISK_PER_TRADE, START, STRATEGY, SYMBOL, seed_engine, build_engine,
)

ANCHOR_SL_MAX = float(os.environ.get("ANCHOR_SL_MAX", 100.0))
ANCHOR_RISK   = float(os.environ.get("ANCHOR_RISK", RISK_PER_TRADE))


def run(label, params, engine_settings, risk=ANCHOR_RISK):
    r = run_backtest(
        strategy_name=STRATEGY, symbol=SYMBOL, interval=INTERVAL,
        start=START, end=END,
        initial_equity=INITIAL_EQUITY, risk_per_trade=risk,
        max_contracts=MAX_CONTRACTS,
        engine_settings=engine_settings,
        strategy_params=params,
    )
    s = summarize(r)
    s["label"] = label
    print(f"{label:<60s} {fmt_summary(s)}")
    return s


def main() -> int:
    print("=" * 110)
    print(f"PHASE 7 — Blackouts + direction @ sl_max={ANCHOR_SL_MAX} r={ANCHOR_RISK*100:.3f}%")
    print("=" * 110)

    base = dict(BASELINE_PARAMS)
    base["sl_max_points"] = ANCHOR_SL_MAX

    print("\n--- 7A: blackout variants ---")
    seed_bo = [(12, 30, 14, 0), (18, 0, 19, 0), (20, 0, 21, 0), (22, 0, 23, 59)]

    variants = {
        "seed BO":                     seed_bo,
        "tighten 12:00-14":            [(12, 0, 14, 0), (18, 0, 19, 0), (20, 0, 21, 0), (22, 0, 23, 59)],
        "loosen 12:30-13:30":          [(12, 30, 13, 30), (18, 0, 19, 0), (20, 0, 21, 0), (22, 0, 23, 59)],
        "block 23 only (free H=22)":   [(12, 30, 14, 0), (18, 0, 19, 0), (20, 0, 21, 0), (23, 0, 23, 59)],
        "extend 17-21 (V1 broad)":     [(12, 30, 14, 0), (17, 0, 21, 0), (22, 0, 23, 59)],
        "+H01":                        seed_bo + [(1, 0, 2, 0)],
        "+H18-21 broad":               [(12, 30, 14, 0), (18, 0, 21, 0), (22, 0, 23, 59)],
        "+H10-11":                     seed_bo + [(10, 0, 11, 0)],
        "tighten + free H22 + add 23": [(12, 0, 14, 0), (18, 0, 19, 0), (20, 0, 21, 0), (23, 0, 23, 59)],
        "drop H20-21 alone":           [(12, 30, 14, 0), (18, 0, 19, 0), (22, 0, 23, 59)],
        "drop H18-19 alone":           [(12, 30, 14, 0), (20, 0, 21, 0), (22, 0, 23, 59)],
        "drop lunch alone":            [(18, 0, 19, 0), (20, 0, 21, 0), (22, 0, 23, 59)],
        "block 15:30-17 only":         [(12, 30, 14, 0), (15, 30, 17, 0), (18, 0, 19, 0), (20, 0, 21, 0), (22, 0, 23, 59)],
    }
    for label, wins in variants.items():
        run(f"BO {label}", base, build_engine(wins))

    print("\n--- 7B: direction restriction via thresholds ---")
    p_long_only = dict(base)
    p_long_only["short_threshold"] = 99
    run("long-only (short_threshold=99)", p_long_only, seed_engine())

    p_short_only = dict(base)
    p_short_only["long_threshold"] = 99
    run("short-only (long_threshold=99)", p_short_only, seed_engine())

    # asymmetric thresholds (mildly favoring one side)
    for lt, st in [(5, 6), (6, 5), (5, 7), (7, 5), (4, 6), (6, 4)]:
        p = dict(base)
        p["long_threshold"]  = lt
        p["short_threshold"] = st
        run(f"asym lt={lt} st={st}", p, seed_engine())

    return 0


if __name__ == "__main__":
    sys.exit(main())
