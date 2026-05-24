"""Phase 13 - Final risk_per_trade squeeze on top of best rr_tp candidates.

Top Pareto candidates from Phase 12:
  rr=1.22 + risk=0.52 %  -> $50,121 / DD $2,377 / WR 53.6 %  ($123 head)
  rr=1.22 + risk=0.50 %  -> $49,016 / DD $2,261 / WR 53.6 %  ($239 head)
  rr=1.28 + risk=0.52 %  -> $49,790 / DD $2,264 / WR 52.6 %  ($236 head)
  rr=1.25 + risk=0.52 %  -> $49,240 / DD $2,321 / WR 52.9 %  ($179 head)
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
    print("Phase 13 - Final risk squeeze")
    print("=" * 80)

    print("\n--- rr=1.22 fine risk squeeze (0.50% -> 0.55% step 0.01%) ---")
    for r in [50, 51, 52, 53, 54, 55]:
        rp = r / 100
        bench(f"rr=1.22 risk={rp:.2f}%",
              **anchor_kwargs(params_override={"rr_tp": 1.22}, risk=rp / 100.0))

    print("\n--- rr=1.25 fine risk squeeze (0.50% -> 0.58%) ---")
    for r in [50, 51, 52, 53, 54, 55, 56, 57, 58]:
        rp = r / 100
        bench(f"rr=1.25 risk={rp:.2f}%",
              **anchor_kwargs(risk=rp / 100.0))

    print("\n--- rr=1.28 fine risk squeeze (0.50% -> 0.56%) ---")
    for r in [50, 51, 52, 53, 54, 55, 56]:
        rp = r / 100
        bench(f"rr=1.28 risk={rp:.2f}%",
              **anchor_kwargs(params_override={"rr_tp": 1.28}, risk=rp / 100.0))


if __name__ == "__main__":
    main()
