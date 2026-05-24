"""Phase 6 - Threshold loosening sweep at the new BO anchor.

Anchor: $37,689 / DD $2,066 / WR 52.5 % / N=1048.
Loosening long_threshold/short_threshold/prep adds eligible trades.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.goals._shared.harness import bench  # noqa: E402
from _anchor import anchor_kwargs  # noqa: E402


def main() -> None:
    print("Phase 6 - Threshold loosening")
    print("=" * 80)

    bench("anchor", **anchor_kwargs())
    print()

    # long_threshold sweep (default 5)
    print("--- long_threshold sweep (short fixed at 5) ---")
    for lt in [3, 4, 5, 6, 7]:
        bench(f"long_threshold={lt}",
              **anchor_kwargs(params_override={"long_threshold": lt}))
    print()

    # short_threshold sweep (long fixed at 5)
    print("--- short_threshold sweep (long fixed at 5) ---")
    for st in [3, 4, 5, 6, 7]:
        bench(f"short_threshold={st}",
              **anchor_kwargs(params_override={"short_threshold": st}))
    print()

    # symmetric threshold sweep
    print("--- symmetric long=short threshold ---")
    for t in [3, 4, 5, 6]:
        bench(f"long=short={t}",
              **anchor_kwargs(params_override={"long_threshold": t, "short_threshold": t}))
    print()

    # prep_threshold sweep
    print("--- long_prep_threshold sweep (default 3) ---")
    for lp in [1, 2, 3, 4]:
        bench(f"long_prep_threshold={lp}",
              **anchor_kwargs(params_override={"long_prep_threshold": lp}))
    print()

    print("--- short_prep_threshold sweep ---")
    for sp in [1, 2, 3, 4]:
        bench(f"short_prep_threshold={sp}",
              **anchor_kwargs(params_override={"short_prep_threshold": sp}))
    print()

    # symmetric prep
    print("--- symmetric long_prep=short_prep ---")
    for p in [1, 2, 3, 4]:
        bench(f"prep={p}",
              **anchor_kwargs(params_override={"long_prep_threshold": p, "short_prep_threshold": p}))


if __name__ == "__main__":
    main()
