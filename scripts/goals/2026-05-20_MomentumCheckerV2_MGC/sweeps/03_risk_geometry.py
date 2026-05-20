"""Phase 3 — Risk geometry (SL & RR).

Direct levers on losing-trade $ size:
  - sl_lookback (how many bars to look back for swing high/low)
  - sl_max_points (cap on SL distance — TIGHTER cap → smaller $ losses)
  - rr_tp (TP at RR=N — higher = bigger wins, but lower hit rate)
  - tick_buffer (extra ticks past swing)

Baseline (V1-compat): PnL=$49,733 / $DD=$3,655 / N=785 / WR=40.1%

V1 MGC values: sl_lookback=15, sl_max_points=50, rr_tp=3.0, tick_buffer=2
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
    print(f"PHASE 3 — Risk geometry  |  {STRATEGY}  {SYMBOL} {INTERVAL}  risk={RISK_PER_TRADE*100:.2f}%")
    print(f"Baseline (V1-compat): PnL=$49,733  $DD=$3,655  N=785")
    print("=" * 110)

    t0 = time.time()
    n = 0

    # 1) sl_lookback (V1 MGC=15; MNQ uses 5)
    print("\n--- 1) sl_lookback ---")
    for slb in (3, 5, 7, 10, 15, 20, 25):
        p = dict(V1_COMPAT_PARAMS); p["sl_lookback"] = slb
        bench(f"sl_lookback={slb}", strategy_params=p, **_common()); n += 1

    # 2) sl_max_points (V1 MGC=50; MNQ winner used 60)
    print("\n--- 2) sl_max_points (cap on SL distance) ---")
    for sl_max in (15, 20, 25, 30, 35, 40, 50, 60, 80, 100):
        p = dict(V1_COMPAT_PARAMS); p["sl_max_points"] = float(sl_max)
        bench(f"sl_max_points={sl_max}", strategy_params=p, **_common()); n += 1

    # 3) rr_tp (V1 MGC=3.0)
    print("\n--- 3) rr_tp ---")
    for rr in (1.5, 2.0, 2.5, 3.0, 3.5, 4.0):
        p = dict(V1_COMPAT_PARAMS); p["rr_tp"] = rr
        bench(f"rr_tp={rr}", strategy_params=p, **_common()); n += 1

    # 4) tick_buffer (V1 MGC=2)
    print("\n--- 4) tick_buffer ---")
    for tb in (0, 1, 2, 3, 5):
        p = dict(V1_COMPAT_PARAMS); p["tick_buffer"] = tb
        bench(f"tick_buffer={tb}", strategy_params=p, **_common()); n += 1

    # 5) Combo: sl_lookback × sl_max — explore the joint best
    print("\n--- 5) Combo: sl_lookback × sl_max ---")
    for slb, slm in product((5, 7, 10), (25, 35, 50)):
        p = dict(V1_COMPAT_PARAMS); p["sl_lookback"] = slb; p["sl_max_points"] = float(slm)
        bench(f"slb={slb}, sl_max={slm}", strategy_params=p, **_common()); n += 1

    elapsed = time.time() - t0
    print(f"\nTotal sims: {n}  |  Elapsed: {elapsed:.1f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
