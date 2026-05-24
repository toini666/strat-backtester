"""Phase 10 - Combine the top Phase-9 Alligator/HMA findings.

Pareto wins from Phase 9 (each vs Phase-8 anchor at PnL $38,533 / DD $2,051):
  lips_length=6   ->  +$2,420 PnL / -$49 DD
  lips_offset=5   ->  +$2,845 PnL / +$5 DD
  jaw_offset=10   ->  +$1,100 PnL / -$40 DD
  jaw_offset=12   ->  +$1,168 PnL / -$40 DD
  hma2_len=76     ->  +$656  PnL / 0 DD
  teeth_length=7  ->  +$495  PnL / -$57 DD
  jaw_length=14   ->  PnL flat   / -$173 DD (DD reducer)
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.goals._shared.harness import bench  # noqa: E402
from _anchor import anchor_kwargs  # noqa: E402


def main() -> None:
    print("Phase 10 - Alligator/HMA combo crystallize")
    print("=" * 80)
    bench("anchor (ema_prin=40)", **anchor_kwargs())

    print("\n--- Top-2 single combos ---")
    bench("L6 + LO5",
          **anchor_kwargs(params_override={"lips_length": 6, "lips_offset": 5}))
    bench("L7 + LO5",
          **anchor_kwargs(params_override={"lips_length": 7, "lips_offset": 5}))
    bench("L6 + LO1",
          **anchor_kwargs(params_override={"lips_length": 6, "lips_offset": 1}))

    print("\n--- Triple combos ---")
    bench("L6 + LO5 + jaw_off=10",
          **anchor_kwargs(params_override={"lips_length": 6, "lips_offset": 5, "jaw_offset": 10}))
    bench("L6 + LO5 + jaw_off=12",
          **anchor_kwargs(params_override={"lips_length": 6, "lips_offset": 5, "jaw_offset": 12}))
    bench("L7 + LO5 + jaw_off=12",
          **anchor_kwargs(params_override={"lips_length": 7, "lips_offset": 5, "jaw_offset": 12}))
    bench("L6 + LO5 + hma2_len=76",
          **anchor_kwargs(params_override={"lips_length": 6, "lips_offset": 5, "hma2_len": 76}))
    bench("L6 + LO5 + teeth_length=7",
          **anchor_kwargs(params_override={"lips_length": 6, "lips_offset": 5, "teeth_length": 7}))
    bench("L6 + LO5 + jaw_length=14",
          **anchor_kwargs(params_override={"lips_length": 6, "lips_offset": 5, "jaw_length": 14}))

    print("\n--- Quad+ combos ---")
    bench("L6 + LO5 + jaw_off=12 + hma2=76",
          **anchor_kwargs(params_override={"lips_length": 6, "lips_offset": 5, "jaw_offset": 12, "hma2_len": 76}))
    bench("L6 + LO5 + jaw_off=12 + teeth_len=7",
          **anchor_kwargs(params_override={"lips_length": 6, "lips_offset": 5, "jaw_offset": 12, "teeth_length": 7}))
    bench("L6 + LO5 + jaw_off=12 + jaw_length=14",
          **anchor_kwargs(params_override={"lips_length": 6, "lips_offset": 5, "jaw_offset": 12, "jaw_length": 14}))
    bench("L6 + LO5 + jaw_off=12 + hma2=76 + jaw_length=14",
          **anchor_kwargs(params_override={"lips_length": 6, "lips_offset": 5, "jaw_offset": 12, "hma2_len": 76, "jaw_length": 14}))
    bench("L7 + LO5 + jaw_off=12 + hma2=76 + jaw_length=14",
          **anchor_kwargs(params_override={"lips_length": 7, "lips_offset": 5, "jaw_offset": 12, "hma2_len": 76, "jaw_length": 14}))
    bench("L6 + LO5 + jaw_off=12 + hma2=76 + teeth_len=7",
          **anchor_kwargs(params_override={"lips_length": 6, "lips_offset": 5, "jaw_offset": 12, "hma2_len": 76, "teeth_length": 7}))


if __name__ == "__main__":
    main()
