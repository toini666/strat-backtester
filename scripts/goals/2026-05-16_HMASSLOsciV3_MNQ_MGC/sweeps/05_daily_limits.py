"""05 — combined daily win/loss limits (after_close mode; intra_bar rejected for multi)."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _campaign import bench  # noqa: E402


def main() -> None:
    print(f"{'='*120}")
    print("05 — daily limits (after_close) at baseline\n")

    print("--- ref")
    bench("baseline (no DL)")

    print("\n--- loss-only DL")
    for ll in (400, 500, 700, 900, 1200, 1500):
        bench(f"DL loss=-{ll}", daily_loss=ll)

    print("\n--- win-only DL")
    for wl in (500, 700, 1000, 1500, 2000):
        bench(f"DL win=+{wl}", daily_win=wl)

    print("\n--- win+loss DL combos")
    for wl, ll in ((500, 700), (700, 700), (1000, 1000), (1000, 700), (1500, 1000), (1500, 1500)):
        bench(f"DL +{wl}/-{ll}", daily_win=wl, daily_loss=ll)


if __name__ == "__main__":
    main()
