"""Phase 5 — Other modules (Supertrend, STC, Alligator, HMA, UT Bot).

UT is currently OFF in the seed — worth trying ON.
Most HMA params are known dead per memory project-mcv2-hma-stack — limited touches.
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
    header("Phase 5a — Supertrend (seed: atr=10, mult=3)")
    for v in [7, 10, 14, 17, 21]:
        bench(f"st_atr={v}", params={"st_atr": v})
    for v in [2.0, 2.5, 3.0, 3.5, 4.0]:
        bench(f"st_mult={v}", params={"st_mult": v})

    header("Phase 5b — STC (seed: length=10, fast=32, slow=50)")
    for v in [6, 8, 10, 12, 14, 16]:
        bench(f"stc_length={v}", params={"stc_length": v})
    for v in [20, 26, 32, 40]:
        bench(f"stc_fast_len={v}", params={"stc_fast_len": v})
    for v in [40, 50, 60, 80]:
        bench(f"stc_slow_len={v}", params={"stc_slow_len": v})

    header("Phase 5c — Alligator (seed lengths 13/8/5, offsets 8/5/3)")
    for jl in [11, 13, 15]:
        for tl in [6, 8, 10]:
            for ll in [3, 5, 7]:
                bench(
                    f"jaw={jl} teeth={tl} lips={ll}",
                    params={"jaw_length": jl, "teeth_length": tl, "lips_length": ll},
                )

    header("Phase 5d — UT Bot ON (seed: OFF)")
    for k in [0.5, 1.0, 1.5, 2.0]:
        for a in [7, 10, 14]:
            bench(
                f"UT ON key={k} atr={a}",
                params={"ut_on": True, "ut_key": k, "ut_atr_period": a},
            )

    header("Phase 5e — HMA (limited — known dead per memory)")
    for am in [1.5, 2.0, 2.5, 3.0]:
        bench(f"amp_mult={am}", params={"amp_mult": am})
    for pol in [-1, 0, 1, 2, 3, 5]:
        bench(f"hma_pol_bars={pol}", params={"hma_pol_bars": pol})
    for w in [3, 5, 7, 10]:
        bench(f"hma_window_bars={w}", params={"hma_window_bars": w})


if __name__ == "__main__":
    main()
