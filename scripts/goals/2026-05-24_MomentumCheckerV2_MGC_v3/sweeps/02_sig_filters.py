"""Phase 2 — SIG filter family (user-requested test of new sig_range_reject).

Tests:
- 2a: sig_range_reject=True × sig_level (NEW reject — user's hypothesis)
- 2b: sig_filter_on=True bonus × sig_level × pts_sig_value (existing bonus)
- 2c: sig_extreme & sig_extreme_filter_on (seed has it on at 15)
- 2d: combo of best from 2a with the +sl_max=120 baseline
- 2e: sig_range_reject combined with rr_tp variants (could shift WR/RR tradeoff)
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
    # 2a: NEW sig_range_reject — user's "median sig zone" hypothesis
    header("Phase 2a — sig_range_reject=True × sig_level (NEW reject)")
    for lvl in [3, 5, 8, 10, 12, 15, 18, 20, 25]:
        bench(
            f"reject lvl={lvl}",
            params={"sig_range_reject": True, "sig_level": float(lvl)},
        )

    # 2b: sig_filter_on bonus — bilateral, may move thresholds
    header("Phase 2b — sig_filter_on=True bonus × sig_level × pts_sig_value")
    for lvl in [5, 10, 15, 20]:
        for pts in [1, 2]:
            bench(
                f"bonus lvl={lvl} pts={pts}",
                params={
                    "sig_filter_on": True,
                    "sig_level": float(lvl),
                    "pts_sig_value": pts,
                },
            )

    # 2c: sig_extreme sweep (seed: filter_on=True at 15)
    header("Phase 2c — sig_extreme sweep (seed=15, filter ON)")
    for ext in [8, 10, 12, 15, 18, 20, 25]:
        bench(f"sig_extreme={ext}", params={"sig_extreme": float(ext)})
    bench("sig_extreme OFF", params={"sig_extreme_filter_on": False})

    # 2d: combo — reject best lvl with sl_max=120 (Phase 1 free win)
    header("Phase 2d — sig_range_reject + sl_max=120 combos")
    for lvl in [10, 12, 15]:
        bench(
            f"reject lvl={lvl} + sl_max=120",
            params={
                "sig_range_reject": True,
                "sig_level": float(lvl),
                "sl_max_points": 120.0,
            },
        )

    # 2e: reject combined with rr_tp variants (WR/RR tradeoff)
    header("Phase 2e — sig_range_reject × rr_tp")
    for lvl in [10, 15]:
        for rr in [2.5, 2.75, 3.0, 3.25]:
            bench(
                f"reject lvl={lvl} rr={rr}",
                params={
                    "sig_range_reject": True,
                    "sig_level": float(lvl),
                    "rr_tp": rr,
                },
            )


if __name__ == "__main__":
    main()
