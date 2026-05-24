"""Phase 16 - Final BO spot-check at winner config.

Buckets from Phase 15 (winner trade stream) showed three half-hour clusters:
  H=07:00  n=32  WR=38%  total=$-873
  H=09:30  n=23  WR=39%  total=$-262
  H=17:30  n=28  WR=43%  total=$-670

Note: BO 07-08 at the winner was tested in Phase 14 (-$1,916 PnL), so the
07:30-08:00 half is positive enough to keep. Test the H=07:00-07:30 half only.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.goals._shared.harness import bench  # noqa: E402
from _anchor import anchor_kwargs, ANCHOR_BOS  # noqa: E402
from _campaign import build_engine_settings  # noqa: E402


WP = {"rr_tp": 1.22}
WR = 0.0053


def main() -> None:
    print("Phase 16 - Final BO spot-check at winner")
    print("=" * 80)
    bench("WINNER (no extra BO)", **anchor_kwargs(params_override=WP, risk=WR))

    candidates = [
        ("WINNER + BO 17:30-18:00", [(17, 30, 18, 0)]),
        ("WINNER + BO 07:00-07:30", [(7, 0, 7, 30)]),
        ("WINNER + BO 09:30-10:00", [(9, 30, 10, 0)]),
        ("WINNER + BO 17:30-18 + 07:00-07:30",
         [(17, 30, 18, 0), (7, 0, 7, 30)]),
        ("WINNER + BO 17:30-18 + 07:00-07:30 + 09:30-10:00",
         [(17, 30, 18, 0), (7, 0, 7, 30), (9, 30, 10, 0)]),
    ]
    for label, extra in candidates:
        es = build_engine_settings(blackouts=list(ANCHOR_BOS) + extra)
        bench(label, **anchor_kwargs(params_override=WP, risk=WR, engine_settings=es))


if __name__ == "__main__":
    main()
