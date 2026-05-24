"""Phase 1 — SL geometry (user-hypothesis area).

This is the heart of the campaign. Tests the user's two new params + the
sl_lookback hypothesis. Independent 1-D sweeps then a key combo grid.

Sub-phases:
- 1a: sl_lookback alone (seed = 15, very wide)
- 1b: sl_min_pct alone (NEW)
- 1c: sl_max_points alone
- 1d: tick_buffer alone
- 1e: rr_tp alone
- 1f: be_at_rr alone
- 1g: KEY COMBO — sl_lookback × sl_min_pct grid (user's specific request)
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
    # 1a: sl_lookback alone
    header("Phase 1a — sl_lookback alone (seed=15)")
    for lb in [3, 5, 7, 10, 15, 20, 25]:
        bench(f"lb={lb}", params={"sl_lookback": lb})

    # 1b: sl_min_pct alone (NEW)
    header("Phase 1b — sl_min_pct alone (seed=0.0, NEW)")
    for mp in [0.0, 0.05, 0.10, 0.15, 0.20, 0.30, 0.50]:
        bench(f"sl_min_pct={mp}", params={"sl_min_pct": mp})

    # 1c: sl_max_points alone
    header("Phase 1c — sl_max_points alone (seed=100)")
    for smp in [40, 60, 80, 100, 120, 150]:
        bench(f"sl_max={smp}", params={"sl_max_points": float(smp)})

    # 1d: tick_buffer alone
    header("Phase 1d — tick_buffer alone (seed=2)")
    for tb in [0, 1, 2, 3]:
        bench(f"tb={tb}", params={"tick_buffer": tb})

    # 1e: rr_tp alone
    header("Phase 1e — rr_tp alone (seed=3.0)")
    for rr in [1.75, 2.0, 2.25, 2.5, 2.75, 3.0, 3.25, 3.5]:
        bench(f"rr_tp={rr}", params={"rr_tp": rr})

    # 1f: be_at_rr alone
    header("Phase 1f — be_at_rr alone (seed=2.0)")
    for be in [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0]:
        bench(f"be_at_rr={be}", params={"be_at_rr": be})

    # 1g: KEY COMBO — sl_lookback × sl_min_pct grid
    header("Phase 1g — KEY combo: sl_lookback × sl_min_pct grid")
    for lb in [3, 5, 7, 10, 15]:
        for mp in [0.0, 0.05, 0.10, 0.15, 0.20]:
            bench(
                f"lb={lb:>2} × mp={mp}",
                params={"sl_lookback": lb, "sl_min_pct": mp},
            )


if __name__ == "__main__":
    main()
