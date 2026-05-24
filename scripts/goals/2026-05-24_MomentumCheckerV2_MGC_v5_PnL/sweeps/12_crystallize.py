"""Phase 12 - Crystallize winner.

Combine the best findings from prior phases and apply final risk squeeze.
Fill in the top-N candidates after the prior phases.
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
    print("Phase 12 - Crystallize")
    print("=" * 80)
    bench("v5 anchor", **anchor_kwargs())

    # PLACEHOLDER - real top combos filled in after Phase 8-11.
    print("\n(Final candidates to be added after Phase 8-11.)")


if __name__ == "__main__":
    main()
