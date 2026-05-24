"""Phase 7 - Strategy params sweep at the new BO anchor.

Thresholds are saturated by min_gap=8. Sweep:
  - min_gap (real entry-volume lever)
  - max_candle_pct (loosen big-bar reject)
  - mf_length (memory: non-monotone on MCV2)
  - mf_smooth
  - hyper_wave_length
  - signal_length
  - hw_level, sig_extreme, sig_level
  - ssl_len, ssl_mult, amp_mult
  - hma_window_bars
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.goals._shared.harness import bench  # noqa: E402
from _anchor import anchor_kwargs  # noqa: E402


def sweep(name, values, key, format_func=str):
    for v in values:
        bench(f"{name}={format_func(v)}", **anchor_kwargs(params_override={key: v}))


def main() -> None:
    print("Phase 7 - Strategy params at anchor")
    print("=" * 80)
    bench("anchor", **anchor_kwargs())

    print("\n--- min_gap (seed=8) ---")
    sweep("min_gap", [4, 5, 6, 7, 8, 9, 10, 12], "min_gap")

    print("\n--- max_candle_pct (seed=0.25) ---")
    sweep("max_candle_pct", [0.15, 0.20, 0.25, 0.30, 0.35, 0.40, 0.50, 0.75], "max_candle_pct")

    print("\n--- mf_length (seed=35, NON-MONOTONE per memory) ---")
    sweep("mf_length", [20, 25, 28, 30, 33, 35, 38, 42, 50], "mf_length")

    print("\n--- mf_smooth (seed=6) ---")
    sweep("mf_smooth", [3, 4, 5, 6, 7, 8, 10], "mf_smooth")

    print("\n--- hyper_wave_length (seed=5) ---")
    sweep("hyper_wave_length", [3, 4, 5, 6, 7, 8, 10], "hyper_wave_length")

    print("\n--- signal_length (seed=3) ---")
    sweep("signal_length", [1, 2, 3, 4, 5, 7], "signal_length")

    print("\n--- hw_level (seed=16) ---")
    sweep("hw_level", [10, 12, 14, 16, 18, 20, 25], "hw_level")

    print("\n--- sig_extreme (seed=15) ---")
    sweep("sig_extreme", [10, 12, 14, 15, 18, 20, 25], "sig_extreme")


if __name__ == "__main__":
    main()
