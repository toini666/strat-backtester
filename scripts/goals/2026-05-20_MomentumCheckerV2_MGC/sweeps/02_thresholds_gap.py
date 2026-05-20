"""Phase 2 — Thresholds, gap, candle filter.

The structural DD won't come down via filters alone (Phase 1 showed
+1k DD when various filters were toggled). This phase tests TIGHTER entry
gates: raise thresholds, raise min_gap, narrow max_candle_pct.

Baseline (V1-compat): PnL=$49,733 / $DD=$3,655 / N=785 / WR=40.1%
"""

from __future__ import annotations

import sys
import time
from itertools import product
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

CAMPAIGN_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CAMPAIGN_DIR / "sweeps"))

from scripts.goals._shared.harness import bench  # noqa: E402

from _campaign import (  # noqa: E402
    END,
    INITIAL_EQUITY,
    INTERVAL,
    MAX_CONTRACTS,
    RISK_PER_TRADE,
    START,
    STRATEGY,
    SYMBOL,
    V1_COMPAT_PARAMS,
    anchor_engine,
)


def _common():
    return dict(
        strategy_name=STRATEGY,
        symbol=SYMBOL,
        interval=INTERVAL,
        start=START,
        end=END,
        initial_equity=INITIAL_EQUITY,
        risk_per_trade=RISK_PER_TRADE,
        max_contracts=MAX_CONTRACTS,
        engine_settings=anchor_engine(),
    )


def main() -> int:
    print("=" * 110)
    print(f"PHASE 2 — Thresholds & gap  |  {STRATEGY}  {SYMBOL} {INTERVAL}  risk={RISK_PER_TRADE*100:.2f}%")
    print(f"Baseline (V1-compat): PnL=$49,733  $DD=$3,655  N=785")
    print("=" * 110)

    t0 = time.time()
    n = 0

    # 1) long/short_threshold up
    print("\n--- 1) Threshold raising (long/short symmetric) ---")
    for th in (5, 6, 7):
        p = dict(V1_COMPAT_PARAMS); p["long_threshold"] = th; p["short_threshold"] = th
        bench(f"th={th}/{th}", strategy_params=p, **_common()); n += 1

    # 2) Asymmetric thresholds
    print("\n--- 2) Asymmetric thresholds (long/short) ---")
    for lt, st in [(5, 6), (6, 5), (6, 7), (7, 6), (7, 5), (5, 7)]:
        p = dict(V1_COMPAT_PARAMS); p["long_threshold"] = lt; p["short_threshold"] = st
        bench(f"th={lt}/{st}", strategy_params=p, **_common()); n += 1

    # 3) prep_threshold raising
    print("\n--- 3) Prep threshold (gating bar count) ---")
    for pt in (2, 3, 4):
        p = dict(V1_COMPAT_PARAMS); p["long_prep_threshold"] = pt; p["short_prep_threshold"] = pt
        bench(f"prep={pt}", strategy_params=p, **_common()); n += 1

    # 4) min_gap
    print("\n--- 4) min_gap ---")
    for mg in (3, 5, 7, 9, 11, 13):
        p = dict(V1_COMPAT_PARAMS); p["min_gap"] = mg
        bench(f"min_gap={mg}", strategy_params=p, **_common()); n += 1

    # 5) max_candle_pct
    print("\n--- 5) max_candle_pct (tighter = narrower entry) ---")
    for mcp in (0.2, 0.25, 0.3, 0.35, 0.4, 0.5, 0.6):
        p = dict(V1_COMPAT_PARAMS); p["max_candle_pct"] = mcp
        bench(f"max_candle_pct={mcp}", strategy_params=p, **_common()); n += 1

    # 6) Combo: high threshold + small candle (anticipate stacking later)
    print("\n--- 6) Combo: tight th × tight candle ---")
    for th, mcp in product((6, 7), (0.2, 0.25, 0.3)):
        p = dict(V1_COMPAT_PARAMS); p["long_threshold"] = th; p["short_threshold"] = th; p["max_candle_pct"] = mcp
        bench(f"th={th} + mcp={mcp}", strategy_params=p, **_common()); n += 1

    elapsed = time.time() - t0
    print(f"\nTotal sims: {n}  |  Elapsed: {elapsed:.1f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
