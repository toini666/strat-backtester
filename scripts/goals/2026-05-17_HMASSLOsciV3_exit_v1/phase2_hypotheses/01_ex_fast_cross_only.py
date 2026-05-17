"""H1 — Skip HW confirmation, close at fast HMA / SSL cross.

Sourced from obs-EX.L.1 (26.5% of trades have HW waiting cost them money).
Expected: REJECT (HW pays in mean) — confirm numerically.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _runner import sweep, save_result


if __name__ == "__main__":
    payload = sweep(
        name="01_ex_fast_cross_only",
        description="EX H1: close immediately at fast HMA/SSL cross, no HW wait.",
        lever="EX",
        angle="L",
        variants=[
            {"label": "ON", "overrides": {"lab_exit_fast_cross_only": True}},
        ],
    )
    save_result("01_ex_fast_cross_only", payload)
