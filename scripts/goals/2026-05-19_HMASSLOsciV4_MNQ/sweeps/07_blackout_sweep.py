"""Phase 7 — Targeted blackout sweep.

Phase 6 surfaced these toxic hours (Brussels):
  H=06: n=49, total=-$2,382 (avg -$49, WR 29%) — strongest candidate
  H=04: n=53, total=-$793   — mild
  H=23: n=8,  total=-$166   — noise

Already in blackout (baseline): 08-09, 11-12, 12-13, 14-15, 22-23:59.
We test (A) adding new windows and (B) removing existing ones to see if any
are no longer load-bearing.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from scripts.goals._shared.engine_settings import make_engine_settings
from scripts.goals._shared.harness import bench

from _campaign import (
    BASELINE_ACTIVE_BLACKOUTS,
    BASELINE_V4_PARAMS,
    END,
    INITIAL_EQUITY,
    INTERVAL,
    MAX_CONTRACTS,
    RISK_PER_TRADE,
    START,
    STRATEGY,
    SYMBOL,
)


def _engine(active_windows: list[dict]):
    return make_engine_settings(STRATEGY, extra_active_windows=active_windows)


def _common(engine):
    return dict(
        strategy_name=STRATEGY,
        symbol=SYMBOL,
        interval=INTERVAL,
        start=START,
        end=END,
        strategy_params=BASELINE_V4_PARAMS,
        initial_equity=INITIAL_EQUITY,
        risk_per_trade=RISK_PER_TRADE,
        max_contracts=MAX_CONTRACTS,
        engine_settings=engine,
    )


def _w(sh, eh, sm=0, em=0):
    return {"start_hour": sh, "start_minute": sm, "end_hour": eh, "end_minute": em}


def main() -> int:
    print("=" * 110)
    print(f"PHASE 7 — Blackout sweep  |  TF={INTERVAL}")
    print("=" * 110)

    base = bench("Baseline (5 active blackouts)", **_common(_engine(BASELINE_ACTIVE_BLACKOUTS)))
    base_ratio = base["net_pnl"] / max(base["max_dd_$"], 1.0)
    print(f"\nBaseline P/DD ratio = {base_ratio:.1f}\n")

    # ===== A. ADD new toxic windows =====
    print("-" * 110)
    print("A. ADD new windows on top of baseline")
    print("-" * 110)

    add_specs = [
        ("+H=06-07",        [_w(6, 7)]),
        ("+H=05-07",        [_w(5, 7)]),
        ("+H=04-07",        [_w(4, 7)]),
        ("+H=06-08",        [_w(6, 8)]),
        ("+H=23-24",        [_w(23, 23, 0, 59)]),  # 23:00–23:59
        ("+H=06-07 +H=23",  [_w(6, 7), _w(23, 23, 0, 59)]),
        ("+H=04-07 +H=23",  [_w(4, 7), _w(23, 23, 0, 59)]),
    ]
    for label, adds in add_specs:
        windows = BASELINE_ACTIVE_BLACKOUTS + adds
        bench(label, **_common(_engine(windows)))

    # ===== B. REMOVE baseline windows individually =====
    print()
    print("-" * 110)
    print("B. REMOVE one baseline window at a time (to check load-bearing-ness)")
    print("-" * 110)

    # Baseline windows as labels
    baseline_pairs = [
        ("08-09",   _w(8, 9)),
        ("11-12",   _w(11, 12)),
        ("12-13",   _w(12, 13)),
        ("14-15",   _w(14, 15)),
    ]
    for label, dropped in baseline_pairs:
        windows = [w for w in BASELINE_ACTIVE_BLACKOUTS if w != dropped]
        bench(f"drop {label}", **_common(_engine(windows)))

    # ===== C. Both directions: KEEP best add + drop weakest baseline =====
    print()
    print("-" * 110)
    print("C. Combine: baseline ± best add and drops")
    print("-" * 110)

    # Try the most promising addition combined with dropping any seemingly-useless baseline
    promising_add = [_w(6, 7)]  # tweak if A surfaces something better
    bench("+H=06-07 only",
          **_common(_engine(BASELINE_ACTIVE_BLACKOUTS + promising_add)))

    return 0


if __name__ == "__main__":
    sys.exit(main())
