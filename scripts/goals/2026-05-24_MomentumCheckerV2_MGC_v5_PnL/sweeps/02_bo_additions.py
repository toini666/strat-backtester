"""Phase 2 - Blackout additions sweep (DD reducers).

From Phase 1 bucket analysis, four half-hour clusters look attractive to BO:
  H=11:30  total=$-1,102  WR=28%  n=18
  H=06:30  total=$  -985  WR=25%  n=12
  H=19:30  total=$  -954  WR=40%  n=15
  H=09:30  total=$  -445  WR=37%  n=19
Also test H=02 (full hour, 45% WR, n=77).

Methodology: add ONE BO at a time, then test best 2-3 combinations.
WR soft floor: 51.5 % (advisor) for noise-buffer against fresh data.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.goals._shared.harness import bench  # noqa: E402
from _campaign import SEED_BLACKOUTS_ACTIVE, build_engine_settings, seed_kwargs  # noqa: E402


def with_extra_bo(*extra):
    bos = list(SEED_BLACKOUTS_ACTIVE) + list(extra)
    return build_engine_settings(blackouts=bos)


def main() -> None:
    print("Phase 2 - BO additions (DD reducers)")
    print("=" * 80)

    # Baseline
    bench("baseline (v4 winner)", **seed_kwargs())
    print()

    # Single-BO additions
    candidates = [
        ("BO + H=11:30-12:00", [(11, 30, 12, 0)]),
        ("BO + H=06:30-07:00", [(6, 30, 7, 0)]),
        ("BO + H=19:30-20:00", [(19, 30, 20, 0)]),
        ("BO + H=09:30-10:00", [(9, 30, 10, 0)]),
        ("BO + H=02:00-03:00", [(2, 0, 3, 0)]),
        ("BO + H=23:00-23:59", [(23, 0, 23, 59)]),  # H=23 has WR 38% n=13
        ("BO + H=17:00-17:30", [(17, 0, 17, 30)]),  # 44% WR n=41
    ]
    results = {}
    for label, extra in candidates:
        es = build_engine_settings(blackouts=list(SEED_BLACKOUTS_ACTIVE) + extra)
        results[label] = bench(label, **seed_kwargs(engine_settings=es))
    print()

    # Top-2-by-DD-improvement combos
    print("--- Pair combinations (top single-BO DD reducers) ---")
    extra_pairs = [
        ("BO + H=11:30 + H=06:30",
         [(11, 30, 12, 0), (6, 30, 7, 0)]),
        ("BO + H=11:30 + H=19:30",
         [(11, 30, 12, 0), (19, 30, 20, 0)]),
        ("BO + H=11:30 + H=09:30",
         [(11, 30, 12, 0), (9, 30, 10, 0)]),
        ("BO + H=06:30 + H=19:30",
         [(6, 30, 7, 0), (19, 30, 20, 0)]),
        ("BO + H=11:30 + H=06:30 + H=19:30",
         [(11, 30, 12, 0), (6, 30, 7, 0), (19, 30, 20, 0)]),
        ("BO + all four halves",
         [(11, 30, 12, 0), (6, 30, 7, 0), (19, 30, 20, 0), (9, 30, 10, 0)]),
    ]
    for label, extra in extra_pairs:
        es = build_engine_settings(blackouts=list(SEED_BLACKOUTS_ACTIVE) + extra)
        results[label] = bench(label, **seed_kwargs(engine_settings=es))


if __name__ == "__main__":
    main()
