"""Phase 6 — Combo lattice: stack the single-lever Pareto+/sideways wins.

Identified Pareto+ levers (vs V1-compat baseline PnL=$49,733 / DD=$3,655):
  A) sl_max_points=80           (+$1,574 PnL, −$366 DD) — biggest win
  B) pts_hma_slow=1 + hma_window_bars=5  (+$1,686 PnL, −$46 DD)
  C) max_candle_pct=0.3         (+$947 PnL, +$0 DD)
  D) ema_sec_len=5              (+$724 PnL, +$0 DD)
  E) be_at_rr=2.0               (−$1,153 PnL, −$199 DD)  — DD lever
  F) tick_buffer=3              (+$285 PnL, +$22 DD)
  G) amp_mult=2.5 (alt)         (−$209 PnL, +$0 DD) — barely changes baseline

Strategy:
  1. Stack A+B+C+D (PnL maximisers, neutral or favorable on DD)
  2. Add E (BE) on top for DD relief
  3. Try sl_max=80 vs 100 once base is built
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


WIN_A = {"sl_max_points": 80.0}
WIN_B = {"pts_hma_slow": 1, "hma_window_bars": 5}
WIN_C = {"max_candle_pct": 0.3}
WIN_D = {"ema_sec_len": 5}
WIN_E = {"be_at_rr": 2.0}
WIN_F = {"tick_buffer": 3}


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


def _merge(*dicts):
    p = dict(V1_COMPAT_PARAMS)
    for d in dicts:
        p.update(d)
    return p


def main() -> int:
    print("=" * 110)
    print(f"PHASE 6 — Combo lattice  |  {STRATEGY}  {SYMBOL} {INTERVAL}  risk={RISK_PER_TRADE*100:.2f}%")
    print(f"Baseline (V1-compat): PnL=$49,733  $DD=$3,655  N=785")
    print("=" * 110)

    t0 = time.time()
    n = 0

    # 1) Pairwise
    print("\n--- 1) Pairwise stacks ---")
    pairs = [
        ("A+B", _merge(WIN_A, WIN_B)),
        ("A+C", _merge(WIN_A, WIN_C)),
        ("A+D", _merge(WIN_A, WIN_D)),
        ("A+E", _merge(WIN_A, WIN_E)),
        ("A+F", _merge(WIN_A, WIN_F)),
        ("B+C", _merge(WIN_B, WIN_C)),
        ("B+D", _merge(WIN_B, WIN_D)),
        ("B+E", _merge(WIN_B, WIN_E)),
        ("C+D", _merge(WIN_C, WIN_D)),
        ("C+E", _merge(WIN_C, WIN_E)),
        ("D+E", _merge(WIN_D, WIN_E)),
    ]
    for lab, p in pairs:
        bench(f"[{lab}]", strategy_params=p, **_common()); n += 1

    # 2) Triplet stacks
    print("\n--- 2) Triplets ---")
    triplets = [
        ("A+B+C", _merge(WIN_A, WIN_B, WIN_C)),
        ("A+B+D", _merge(WIN_A, WIN_B, WIN_D)),
        ("A+B+E", _merge(WIN_A, WIN_B, WIN_E)),
        ("A+C+D", _merge(WIN_A, WIN_C, WIN_D)),
        ("A+C+E", _merge(WIN_A, WIN_C, WIN_E)),
        ("A+D+E", _merge(WIN_A, WIN_D, WIN_E)),
        ("B+C+D", _merge(WIN_B, WIN_C, WIN_D)),
        ("B+C+E", _merge(WIN_B, WIN_C, WIN_E)),
        ("B+D+E", _merge(WIN_B, WIN_D, WIN_E)),
        ("C+D+E", _merge(WIN_C, WIN_D, WIN_E)),
    ]
    for lab, p in triplets:
        bench(f"[{lab}]", strategy_params=p, **_common()); n += 1

    # 3) Quadruplets and quintuplets
    print("\n--- 3) Quadruplets + quintuplets ---")
    quads = [
        ("A+B+C+D",   _merge(WIN_A, WIN_B, WIN_C, WIN_D)),
        ("A+B+C+E",   _merge(WIN_A, WIN_B, WIN_C, WIN_E)),
        ("A+B+D+E",   _merge(WIN_A, WIN_B, WIN_D, WIN_E)),
        ("A+C+D+E",   _merge(WIN_A, WIN_C, WIN_D, WIN_E)),
        ("B+C+D+E",   _merge(WIN_B, WIN_C, WIN_D, WIN_E)),
        ("A+B+C+D+E", _merge(WIN_A, WIN_B, WIN_C, WIN_D, WIN_E)),
        ("A+B+C+D+F", _merge(WIN_A, WIN_B, WIN_C, WIN_D, WIN_F)),
        ("A+B+C+D+E+F", _merge(WIN_A, WIN_B, WIN_C, WIN_D, WIN_E, WIN_F)),
    ]
    for lab, p in quads:
        bench(f"[{lab}]", strategy_params=p, **_common()); n += 1

    # 4) sl_max variations around the new best combos
    print("\n--- 4) sl_max variations (60/70/80/90/100) on top combo ---")
    for slm in (60, 70, 80, 90, 100):
        p = _merge(WIN_B, WIN_C, WIN_D)
        p["sl_max_points"] = float(slm)
        bench(f"[B+C+D, sl_max={slm}]", strategy_params=p, **_common()); n += 1
    for slm in (60, 70, 80, 90, 100):
        p = _merge(WIN_B, WIN_C, WIN_D, WIN_E)
        p["sl_max_points"] = float(slm)
        bench(f"[B+C+D+E, sl_max={slm}]", strategy_params=p, **_common()); n += 1

    elapsed = time.time() - t0
    print(f"\nTotal sims: {n}  |  Elapsed: {elapsed:.1f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
