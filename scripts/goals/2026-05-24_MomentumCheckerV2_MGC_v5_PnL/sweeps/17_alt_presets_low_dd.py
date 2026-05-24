"""Phase 17 - Map Pareto curve at lower DD on the winner config.

Goal: produce ALT presets with DD close to $2,000 for the user to choose from.
All on winner config (rr=1.22, sl_max=80, L6+LO5+hma2=76, ema_prin=40).
Only risk varies. Also probe one config without rr_tp tweak (keeps seed 1.25).
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
    print("Phase 17 - ALT presets (low-DD Pareto curve)")
    print("=" * 80)

    print("\n--- rr=1.22 risk grid 0.36% -> 0.50% (fine) ---")
    for r in [36, 38, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50]:
        bench(f"rr=1.22 risk=0.{r:02d}%",
              **anchor_kwargs(params_override={"rr_tp": 1.22}, risk=r / 10000.0))

    print("\n--- rr=1.25 (seed) risk grid 0.36% -> 0.50% ---")
    for r in [36, 40, 42, 45, 46, 48, 50]:
        bench(f"rr=1.25 risk=0.{r:02d}%",
              **anchor_kwargs(risk=r / 10000.0))


if __name__ == "__main__":
    main()
