"""Phase 3 — Oscillator core params.

Memory: mf_length is NON-monotone — sweep fine.
seed: mf_length=35, mf_smooth=6, hyper_wave_length=5, signal_length=3,
signal_type=SMA, hw_level=16, max_candle_pct=0.25, delta_off_mode=both
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
    header("Phase 3a — mf_length (NON-monotone, sweep fine)")
    for v in [20, 25, 28, 30, 32, 35, 38, 40, 45, 50, 55]:
        bench(f"mf_length={v}", params={"mf_length": v})

    header("Phase 3b — mf_smooth (seed=6)")
    for v in [3, 4, 5, 6, 7, 8, 10]:
        bench(f"mf_smooth={v}", params={"mf_smooth": v})

    header("Phase 3c — hyper_wave_length (seed=5)")
    for v in [3, 4, 5, 6, 7, 8, 10]:
        bench(f"hyper_wave_length={v}", params={"hyper_wave_length": v})

    header("Phase 3d — signal_length (seed=3)")
    for v in [2, 3, 4, 5, 6]:
        bench(f"signal_length={v}", params={"signal_length": v})

    header("Phase 3e — signal_type (seed=SMA)")
    for v in ["SMA", "EMA", "WMA"]:
        bench(f"signal_type={v}", params={"signal_type": v})

    header("Phase 3f — hw_level (seed=16)")
    for v in [8, 10, 12, 14, 16, 18, 20, 22]:
        bench(f"hw_level={v}", params={"hw_level": float(v)})

    header("Phase 3g — hw_extreme_filter_on toggle + hw_extreme (seed=OFF/15)")
    bench("hw_ext OFF (seed)", params={"hw_extreme_filter_on": False})
    for v in [10, 15, 18, 20, 25, 30]:
        bench(f"hw_ext ON ext={v}", params={"hw_extreme_filter_on": True, "hw_extreme": float(v)})

    header("Phase 3h — max_candle_pct (seed=0.25)")
    for v in [0.15, 0.18, 0.20, 0.22, 0.25, 0.28, 0.30, 0.35]:
        bench(f"mcp={v}", params={"max_candle_pct": v})

    header("Phase 3i — delta_off_mode + cloud_zero")
    for m in ["both", "counter_trend"]:
        for cz in [False, True]:
            bench(
                f"delta_off={m} cloud_zero={cz}",
                params={"delta_off_mode": m, "cloud_zero_filter_on": cz},
            )

    header("Phase 3j — cloud_filter_on + delta_filter_on toggles")
    for cf in [True, False]:
        for df in [True, False]:
            bench(f"cloud={cf} delta={df}", params={"cloud_filter_on": cf, "delta_filter_on": df})


if __name__ == "__main__":
    main()
