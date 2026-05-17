"""H3 — Exit on contra canal HMA flip.

Sourced from obs-EX.L.3 (27% of trades have a contra flip during life).
Expected: REJECT (flip-as-exit averages worse than real exit).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _runner import sweep, save_result


if __name__ == "__main__":
    payload = sweep(
        name="03_ex_on_canal_flip",
        description="EX H3: close on contra-direction HMA canal flip.",
        lever="EX",
        angle="L",
        variants=[
            {"label": "ON", "overrides": {"lab_exit_on_canal_flip": True}},
        ],
    )
    save_result("03_ex_on_canal_flip", payload)
