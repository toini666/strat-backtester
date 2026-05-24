"""Phase 11 - sl_lookback + tick_buffer + be_at_rr at new anchor."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.goals._shared.harness import bench  # noqa: E402
from _anchor import anchor_kwargs  # noqa: E402


def main() -> None:
    print("Phase 11 - sl_lookback / tick_buffer / be_at_rr at WINNER candidate")
    print("=" * 80)
    # Run at the locked winner config: anchor + rr=1.22 + risk=0.53%
    WP = {"rr_tp": 1.22}
    WR = 0.0053
    bench("WINNER (rr=1.22 lb=14 tb=0 be=2 risk=0.53%)",
          **anchor_kwargs(params_override=WP, risk=WR))

    print("\n--- sl_lookback (seed=14) ---")
    for lb in [8, 10, 11, 12, 13, 14, 15, 16, 18, 20]:
        bench(f"sl_lookback={lb}",
              **anchor_kwargs(params_override={**WP, "sl_lookback": lb}, risk=WR))

    print("\n--- tick_buffer (seed=0) ---")
    for tb in [0, 1, 2, 3, 4]:
        bench(f"tick_buffer={tb}",
              **anchor_kwargs(params_override={**WP, "tick_buffer": tb}, risk=WR))

    print("\n--- be_at_rr (seed=2) ---")
    for be in [1, 1.5, 2, 2.5, 3]:
        bench(f"be_at_rr={be}",
              **anchor_kwargs(params_override={**WP, "be_at_rr": be}, risk=WR))

    print("\n--- sl_max_points (seed=120) ---")
    for sm in [60, 80, 100, 120, 150, 200]:
        bench(f"sl_max_points={sm}",
              **anchor_kwargs(params_override={**WP, "sl_max_points": sm}, risk=WR))


if __name__ == "__main__":
    main()
