"""Phase 9 - Alligator + HMA stack length tweaks at anchor.

Memory: project_mcv2_hma_stack flags LONG HMAs (42/84) as required — V3-style
short lengths (9/34) cause catastrophic DD. Don't sweep too far from defaults.
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
    print("Phase 9 - Alligator + HMA at anchor")
    print("=" * 80)
    bench("anchor", **anchor_kwargs())

    print("\n--- jaw_length (seed=13) ---")
    sweep("jaw_length", [10, 11, 12, 13, 14, 15, 17, 20], "jaw_length")

    print("\n--- teeth_length (seed=8) ---")
    sweep("teeth_length", [5, 6, 7, 8, 9, 10, 12], "teeth_length")

    print("\n--- lips_length (seed=5) ---")
    sweep("lips_length", [3, 4, 5, 6, 7, 8], "lips_length")

    print("\n--- jaw_offset (seed=8) ---")
    sweep("jaw_offset", [5, 6, 7, 8, 9, 10, 12], "jaw_offset")

    print("\n--- teeth_offset (seed=5) ---")
    sweep("teeth_offset", [3, 4, 5, 6, 7, 8], "teeth_offset")

    print("\n--- lips_offset (seed=3) ---")
    sweep("lips_offset", [1, 2, 3, 4, 5], "lips_offset")

    print("\n--- hma1_len (seed=42, stay LONG) ---")
    sweep("hma1_len", [35, 38, 42, 46, 50, 55], "hma1_len")

    print("\n--- hma2_len (seed=84, stay LONG) ---")
    sweep("hma2_len", [70, 76, 84, 92, 100, 110], "hma2_len")

    print("\n--- hma_ema_len (seed=7) ---")
    sweep("hma_ema_len", [3, 5, 7, 9, 12], "hma_ema_len")


if __name__ == "__main__":
    main()
