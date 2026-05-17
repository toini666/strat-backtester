"""H2 — Wait HW, but close only if in-profit at HW arrival.

Sourced from obs-EX.L.1. Implementation: partial 100% at HW cross bars,
simulator's in-profit gate filters losers.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _runner import sweep, save_result


if __name__ == "__main__":
    payload = sweep(
        name="02_ex_hw_only_if_profit",
        description="EX H2: keep V3 fast-cross arming, but at HW only close if in profit.",
        lever="EX",
        angle="L",
        variants=[
            {"label": "ON", "overrides": {"lab_exit_hw_only_if_profit": True}},
        ],
    )
    save_result("02_ex_hw_only_if_profit", payload)
