"""Phase 14 - Final cleanup at top candidate (rr=1.22 + risk=0.53%).

Test remaining hypotheses:
  - Finer risk steps (0.531%, 0.532%, 0.534%) for rounding-cell exploration
  - Stacking teeth_length=7 / jaw_offset=12 with the new anchor
  - ut_on K=2.0 at risk lowered to compensate DD bump
  - sig_extreme bump now that we have a bigger DD margin
  - BO 07-08 / 22-23:59 spot-check (they were removed in Phase 5)
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


WINNER_RR = 1.22
WINNER_RISK = 0.0053


def main() -> None:
    print("Phase 14 - Final cleanup")
    print("=" * 80)
    bench("WINNER candidate (rr=1.22 risk=0.53%)",
          **anchor_kwargs(params_override={"rr_tp": WINNER_RR}, risk=WINNER_RISK))

    print("\n--- Stack teeth_length=7 / jaw_offset=12 / jaw_length=14 ---")
    for tweak in [
        {"teeth_length": 7},
        {"jaw_offset": 12},
        {"jaw_length": 14},
        {"jaw_offset": 12, "teeth_length": 7},
        {"jaw_offset": 12, "jaw_length": 14},
    ]:
        params = {"rr_tp": WINNER_RR, **tweak}
        label = "winner + " + " + ".join(f"{k}={v}" for k, v in tweak.items())
        bench(label, **anchor_kwargs(params_override=params, risk=WINNER_RISK))

    print("\n--- Finer risk steps (0.531-0.535%) ---")
    for r_int in [528, 530, 532, 534, 536]:
        rp = r_int / 1000 / 10  # convert to ratio: 528 -> 0.0528?  We want 528 -> 0.00528
        # actually we want risk in basis points / 1000? Let me use 0.001%
        bench(f"rr=1.22 risk={r_int/100:.3f}%",
              **anchor_kwargs(params_override={"rr_tp": WINNER_RR}, risk=r_int / 100 / 100))

    print("\n--- sig_extreme bump at winner ---")
    for sx in [15, 18, 20, 22, 25]:
        bench(f"sig_extreme={sx}",
              **anchor_kwargs(params_override={"rr_tp": WINNER_RR, "sig_extreme": sx}, risk=WINNER_RISK))

    print("\n--- BO 07-08 / 22-23:59 spot-recheck at new winner ---")
    for label, bos_add in [
        ("winner + BO 07-08", [(7, 0, 8, 0)]),
        ("winner + BO 22-23:59", [(22, 0, 23, 59)]),
    ]:
        es = build_engine_settings(blackouts=list(ANCHOR_BOS) + bos_add)
        bench(label,
              **anchor_kwargs(params_override={"rr_tp": WINNER_RR},
                              risk=WINNER_RISK,
                              engine_settings=es))


if __name__ == "__main__":
    main()
