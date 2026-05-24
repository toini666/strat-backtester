"""Phase 4 - Toggle-off-one-at-a-time BO removal, on top of the best BO stack.

Anchor (Phase 3 winner): v4 BOs + H=02 + H=06:30 + H=11:30 + H=19:30
  -> PnL $31,776 / DD $2,165 / WR 52.4 % / N=973

Each of the 7 original v4 BOs was sized at rr_tp=3 (seed). At rr_tp=1.25 the
strategy economics differ. Removing a BO that's no longer load-bearing should
add trades at neutral-or-positive PnL.
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
    # v4 BOs
    (7, 0, 8, 0),
    (12, 0, 12, 30),
    (12, 30, 14, 0),
    (15, 30, 17, 0),
    (18, 0, 19, 0),
    (20, 0, 21, 0),
    (22, 0, 23, 59),
    # Phase-3 additions
    (2, 0, 3, 0),
    (6, 30, 7, 0),
    (11, 30, 12, 0),
    (19, 30, 20, 0),
]


def main() -> None:
    print("Phase 4 - BO removal (one-at-a-time) on Phase-3 anchor")
    print("=" * 80)

    bench("anchor (all 11 BOs)", **seed_kwargs(engine_settings=build_engine_settings(blackouts=ANCHOR_BOS)))
    print()

    for i, bo in enumerate(ANCHOR_BOS):
        reduced = [b for j, b in enumerate(ANCHOR_BOS) if j != i]
        label = f"remove BO ({bo[0]:02d}:{bo[1]:02d}-{bo[2]:02d}:{bo[3]:02d})"
        bench(label, **seed_kwargs(engine_settings=build_engine_settings(blackouts=reduced)))


if __name__ == "__main__":
    main()
