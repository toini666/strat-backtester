"""Phase 6 — Thresholds, min_gap, and selected point weights.

Memory: at uniform pts=1 the score saturates, so most thresholds are dead.
But we'll re-test in case prior phases changed scoring topology.
"""
from __future__ import annotations

import sys
from pathlib import Path

CAMPAIGN = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CAMPAIGN / "sweeps"))

from _helper import bench  # type: ignore


def header(title: str) -> None:
    print("\n" + "=" * 78)
    print(f"  {title}")
    print("=" * 78)


def main() -> None:
    header("Phase 6a — long_threshold × short_threshold (asymmetric)")
    for lt in [4, 5, 6, 7]:
        for st in [4, 5, 6, 7]:
            bench(
                f"lt={lt} st={st}",
                params={"long_threshold": lt, "short_threshold": st},
            )

    header("Phase 6b — min_gap (seed=8)")
    for v in [4, 5, 6, 7, 8, 9, 10, 11, 12]:
        bench(f"min_gap={v}", params={"min_gap": v})

    header("Phase 6c — Selected point-weight perturbations")
    # MGC v2 found pts perturbations dead; spot-check the most-likely useful ones
    for k in ["pts_hma_slow", "pts_hma_break", "pts_cloud_zero", "pts_st",
              "pts_ema_align", "pts_ema_break", "pts_alligator", "pts_ut_bot"]:
        for v in [0, 2]:
            bench(f"{k}={v}", params={k: v})


if __name__ == "__main__":
    main()
