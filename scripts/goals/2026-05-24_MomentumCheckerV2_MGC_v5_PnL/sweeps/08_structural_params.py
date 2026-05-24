"""Phase 8 - Structural / length params sweep at anchor.

Covered: ssl_*, hma_window_bars, amp_mult, ema_*, alligator lengths, st_*, stc_*.
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
    print("Phase 8 - Structural params at anchor")
    print("=" * 80)
    bench("anchor", **anchor_kwargs())

    print("\n--- ssl_len (seed=60) ---")
    sweep("ssl_len", [30, 40, 50, 60, 70, 80, 100], "ssl_len")

    print("\n--- ssl_mult (seed=0.2) ---")
    sweep("ssl_mult", [0.0, 0.1, 0.15, 0.2, 0.25, 0.3, 0.4], "ssl_mult")

    print("\n--- amp_mult (seed=2) ---")
    sweep("amp_mult", [1, 2, 3, 4], "amp_mult")

    print("\n--- hma_window_bars (seed=5) ---")
    sweep("hma_window_bars", [2, 3, 4, 5, 6, 7, 10], "hma_window_bars")

    print("\n--- ema_prin_len (seed=30) ---")
    sweep("ema_prin_len", [15, 20, 25, 30, 35, 40, 50], "ema_prin_len")

    print("\n--- ema_sec_len (seed=5) ---")
    sweep("ema_sec_len", [3, 4, 5, 6, 7, 8, 10], "ema_sec_len")

    print("\n--- st_atr (seed=10) ---")
    sweep("st_atr", [7, 10, 14, 20], "st_atr")

    print("\n--- st_mult (seed=3) ---")
    sweep("st_mult", [2, 2.5, 3, 3.5, 4], "st_mult")

    print("\n--- stc_length (seed=10) ---")
    sweep("stc_length", [6, 8, 10, 12, 15, 20], "stc_length")

    print("\n--- stc_fast_len (seed=32) ---")
    sweep("stc_fast_len", [20, 25, 32, 40, 50], "stc_fast_len")

    print("\n--- stc_slow_len (seed=50) ---")
    sweep("stc_slow_len", [40, 50, 60, 70, 80], "stc_slow_len")


if __name__ == "__main__":
    main()
