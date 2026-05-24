"""Phase 5 - Combine BO removals on the Phase-3 anchor.

Two single-removal Pareto wins:
  remove (22:00-23:59) -> PnL $35,927 / DD $2,051 / WR 52.5 %
  remove (07:00-08:00) -> PnL $33,528 / DD $2,165 / WR 52.4 %
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.goals._shared.harness import bench  # noqa: E402
from _campaign import build_engine_settings, seed_kwargs  # noqa: E402


ANCHOR_BOS = [
    (7, 0, 8, 0),         # 0  - removing helps
    (12, 0, 12, 30),      # 1
    (12, 30, 14, 0),      # 2
    (15, 30, 17, 0),      # 3
    (18, 0, 19, 0),       # 4
    (20, 0, 21, 0),       # 5
    (22, 0, 23, 59),      # 6  - removing helps a lot
    (2, 0, 3, 0),         # 7
    (6, 30, 7, 0),        # 8
    (11, 30, 12, 0),      # 9
    (19, 30, 20, 0),      # 10
]


def remove_idx(*idx):
    return [b for i, b in enumerate(ANCHOR_BOS) if i not in idx]


def main() -> None:
    print("Phase 5 - BO removal combos")
    print("=" * 80)

    bench("anchor (all 11)", **seed_kwargs(engine_settings=build_engine_settings(blackouts=ANCHOR_BOS)))
    print()

    combos = [
        ("remove (22-23:59) + (07-08)", remove_idx(6, 0)),
        ("remove (22-23:59) + (18-19)", remove_idx(6, 4)),
        ("remove (22-23:59) + (20-21)", remove_idx(6, 5)),
        ("remove (22-23:59) + (15:30-17)", remove_idx(6, 3)),
        ("remove (22-23:59) + (12-12:30)", remove_idx(6, 1)),
        ("remove (22-23:59) + (07-08) + (18-19)", remove_idx(6, 0, 4)),
        ("remove (22-23:59) + (07-08) + (20-21)", remove_idx(6, 0, 5)),
        ("remove (22-23:59) + (07-08) + (18-19) + (20-21)", remove_idx(6, 0, 4, 5)),
        ("remove (22-23:59) + (07-08) + (12-12:30)", remove_idx(6, 0, 1)),
    ]
    for label, bos in combos:
        bench(label, **seed_kwargs(engine_settings=build_engine_settings(blackouts=bos)))


if __name__ == "__main__":
    main()
