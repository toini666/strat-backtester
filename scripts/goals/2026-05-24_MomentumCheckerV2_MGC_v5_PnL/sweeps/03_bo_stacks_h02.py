"""Phase 3 - Stack H=02 BO (big DD reducer) on top of best Phase-2 combos.

H=02 alone reduced DD from $2,438 to $1,921 (-$517) at PnL roughly unchanged.
Pareto winners from Phase 2: H=06:30, H=11:30, H=19:30, H=02:00.
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
    print("Phase 3 - H=02 stacking with Phase-2 winners")
    print("=" * 80)

    combos = [
        ("BO + H=02 + H=06:30", [(2, 0, 3, 0), (6, 30, 7, 0)]),
        ("BO + H=02 + H=11:30", [(2, 0, 3, 0), (11, 30, 12, 0)]),
        ("BO + H=02 + H=19:30", [(2, 0, 3, 0), (19, 30, 20, 0)]),
        ("BO + H=02 + H=06:30 + H=11:30",
         [(2, 0, 3, 0), (6, 30, 7, 0), (11, 30, 12, 0)]),
        ("BO + H=02 + H=06:30 + H=19:30",
         [(2, 0, 3, 0), (6, 30, 7, 0), (19, 30, 20, 0)]),
        ("BO + H=02 + H=11:30 + H=19:30",
         [(2, 0, 3, 0), (11, 30, 12, 0), (19, 30, 20, 0)]),
        ("BO + H=02 + H=06:30 + H=11:30 + H=19:30 (full)",
         [(2, 0, 3, 0), (6, 30, 7, 0), (11, 30, 12, 0), (19, 30, 20, 0)]),
    ]
    for label, extra in combos:
        es = build_engine_settings(blackouts=list(SEED_BLACKOUTS_ACTIVE) + extra)
        bench(label, **seed_kwargs(engine_settings=es))

    # Test narrower H=02 (only worst halves)
    print()
    print("--- Narrower H=02 alternatives ---")
    h02_narrow = [
        ("BO + H=02:00-02:30 only", [(2, 0, 2, 30)]),
        ("BO + H=02:30-03:00 only", [(2, 30, 3, 0)]),
    ]
    for label, extra in h02_narrow:
        es = build_engine_settings(blackouts=list(SEED_BLACKOUTS_ACTIVE) + extra)
        bench(label, **seed_kwargs(engine_settings=es))


if __name__ == "__main__":
    main()
