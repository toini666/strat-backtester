"""Phase 4 — Module toggles + sub-filter triage + point weights.

Tests:
  1) Each module ON/OFF (osc, ema, st, alligator, ut, stc, hma) — to see
     if dropping a module reduces DD without killing PnL.
  2) Per-module sub-filters (osc & alligator have multiple toggles).
  3) Point weight perturbations (pts_* dialed up/down to bias entries).
  4) ut_on=True (V1 MGC had it OFF — V2 MNQ winner had ON).

Baseline (V1-compat): PnL=$49,733 / $DD=$3,655 / N=785 / WR=40.1%
"""

from __future__ import annotations

import sys
import time
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
    print(f"PHASE 4 — Module toggles  |  {STRATEGY}  {SYMBOL} {INTERVAL}  risk={RISK_PER_TRADE*100:.2f}%")
    print(f"Baseline (V1-compat): PnL=$49,733  $DD=$3,655  N=785")
    print("=" * 110)

    t0 = time.time()
    n = 0

    # 1) Module on/off
    print("\n--- 1) Module on/off ---")
    for mod in ("osc_on", "ema_on", "st_on", "alligator_on", "stc_on", "hma_on"):
        p = dict(V1_COMPAT_PARAMS); p[mod] = False
        bench(f"{mod}=False", strategy_params=p, **_common()); n += 1
    # ut_on=True (V1 had False)
    p = dict(V1_COMPAT_PARAMS); p["ut_on"] = True
    bench("ut_on=True (V1 had False)", strategy_params=p, **_common()); n += 1

    # 2) Osc sub-filters
    print("\n--- 2) Oscillator sub-filters ---")
    for f, on in [("hw_filter_on", False), ("cloud_filter_on", False), ("delta_filter_on", False),
                  ("sig_extreme_filter_on", False)]:
        p = dict(V1_COMPAT_PARAMS); p[f] = on
        bench(f"{f}={on}", strategy_params=p, **_common()); n += 1

    # 3) Point weights — bias the score
    print("\n--- 3) Point weights perturbations ---")
    # Boost HMA bucket
    p = dict(V1_COMPAT_PARAMS); p["pts_hma_break"] = 2
    bench("pts_hma_break=2 (boost HMA)", strategy_params=p, **_common()); n += 1
    # Boost EMA bucket
    p = dict(V1_COMPAT_PARAMS); p["pts_ema_break"] = 2; p["pts_ema_align"] = 2
    bench("EMA pts ×2", strategy_params=p, **_common()); n += 1
    # Boost alligator bucket
    p = dict(V1_COMPAT_PARAMS); p["pts_alligator"] = 2; p["pts_alli_offset"] = 2; p["pts_retest_lips"] = 2
    bench("alligator pts ×2", strategy_params=p, **_common()); n += 1
    # Boost ST
    p = dict(V1_COMPAT_PARAMS); p["pts_st"] = 2
    bench("pts_st=2", strategy_params=p, **_common()); n += 1
    # Boost STC
    p = dict(V1_COMPAT_PARAMS); p["pts_stc"] = 2
    bench("pts_stc=2", strategy_params=p, **_common()); n += 1
    # Zero some buckets to remove their weight
    for f in ("pts_hw_sens", "pts_hw_value", "pts_sig_extreme", "pts_cloud", "pts_delta",
              "pts_ema_break", "pts_ema_align", "pts_st", "pts_stc",
              "pts_alligator", "pts_alli_offset", "pts_retest_lips", "pts_hma_break"):
        p = dict(V1_COMPAT_PARAMS); p[f] = 0
        bench(f"{f}=0", strategy_params=p, **_common()); n += 1

    # 4) STC bounds — tighter STC range
    print("\n--- 4) STC bounds (entry-side filter) ---")
    for lo, hi in [(20, 80), (10, 90), (5, 95), (15, 85), (25, 75)]:
        p = dict(V1_COMPAT_PARAMS)
        p["stc_min_long"] = float(lo); p["stc_max_long"] = float(hi)
        p["stc_min_short"] = float(lo); p["stc_max_short"] = float(hi)
        bench(f"stc_range={lo}-{hi}", strategy_params=p, **_common()); n += 1

    elapsed = time.time() - t0
    print(f"\nTotal sims: {n}  |  Elapsed: {elapsed:.1f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
