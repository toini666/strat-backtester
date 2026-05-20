"""Phase 1 — V2-new features single-lever sweep on MGC.

Tests each V2 feature in isolation from the V1-compat baseline to find
which ones reduce DD and/or improve PnL.

Levers tested:
  - delta_off_mode: "both" (baseline) vs "counter_trend"
  - hma_pol_bars:  -1 (baseline) vs 0, 3, 5  (HMA polarity tolerance)
  - pts_hma_slow + hma_window_bars: 0/0 (baseline) vs 1/3, 1/5, 1/10
  - hw_extreme_filter_on: False (baseline) vs True at threshold 15/20/25
  - sig_extreme threshold: 15 (baseline) vs 20, 25, 30, 35, 40
  - cloud_zero_filter_on: False (baseline) vs True (pts_cloud_zero=1)
  - be_at_rr: 0 (baseline) vs 0.5, 1.0, 1.5
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
    print(f"PHASE 1 — V2-new features sweep  |  {STRATEGY}  {SYMBOL} {INTERVAL}  risk={RISK_PER_TRADE*100:.2f}%")
    print(f"Baseline (V1-compat): PnL=$49,733  $DD=$3,655  N=785  WR=40.1%  PF=1.42")
    print("=" * 110)

    t0 = time.time()
    n = 0

    # 1) delta_off_mode
    print("\n--- 1) delta_off_mode ---")
    p = dict(V1_COMPAT_PARAMS); p["delta_off_mode"] = "counter_trend"
    bench("delta_off_mode=counter_trend", strategy_params=p, **_common()); n += 1

    # 2) hma_pol_bars
    print("\n--- 2) hma_pol_bars (polarity tolerance) ---")
    for hpb in (0, 3, 5):
        p = dict(V1_COMPAT_PARAMS); p["hma_pol_bars"] = hpb
        bench(f"hma_pol_bars={hpb}", strategy_params=p, **_common()); n += 1

    # 3) pts_hma_slow + hma_window_bars (V2 SSL cross bucket)
    print("\n--- 3) pts_hma_slow + hma_window_bars (V2 SSL bucket) ---")
    for hwb in (3, 5, 10):
        p = dict(V1_COMPAT_PARAMS); p["pts_hma_slow"] = 1; p["hma_window_bars"] = hwb
        bench(f"pts_hma_slow=1, hma_window_bars={hwb}", strategy_params=p, **_common()); n += 1

    # 4) hw_extreme_filter (was OFF in V1 MGC)
    print("\n--- 4) hw_extreme_filter ON ---")
    for hwe in (15, 20, 25):
        p = dict(V1_COMPAT_PARAMS); p["hw_extreme_filter_on"] = True; p["hw_extreme"] = float(hwe)
        bench(f"hw_extreme_filter=ON @ {hwe}", strategy_params=p, **_common()); n += 1

    # 5) sig_extreme threshold (V1 MGC had it=15, MNQ winner had 40)
    print("\n--- 5) sig_extreme threshold (already filter_on=True) ---")
    for sx in (20, 25, 30, 35, 40):
        p = dict(V1_COMPAT_PARAMS); p["sig_extreme"] = float(sx)
        bench(f"sig_extreme={sx}", strategy_params=p, **_common()); n += 1

    # 6) cloud_zero_filter
    print("\n--- 6) cloud_zero_filter ON ---")
    p = dict(V1_COMPAT_PARAMS); p["cloud_zero_filter_on"] = True; p["pts_cloud_zero"] = 1
    bench("cloud_zero_filter=ON", strategy_params=p, **_common()); n += 1

    # 7) be_at_rr (break-even at RR)
    print("\n--- 7) be_at_rr (move SL to entry at RR>=N) ---")
    for be in (0.5, 1.0, 1.5, 2.0):
        p = dict(V1_COMPAT_PARAMS); p["be_at_rr"] = be
        bench(f"be_at_rr={be}", strategy_params=p, **_common()); n += 1

    elapsed = time.time() - t0
    print(f"\nTotal sims: {n}  |  Elapsed: {elapsed:.1f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
