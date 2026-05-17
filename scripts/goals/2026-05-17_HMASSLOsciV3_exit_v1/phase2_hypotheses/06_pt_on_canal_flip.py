"""H7 — Partial X% at contra canal flip (in-profit only).

Sourced from obs-EX.L.3 / PT.W.2: flip-as-exit is worse on avg but as a partial
might cap tail of risk without killing winners.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _runner import sweep, save_result


if __name__ == "__main__":
    payload = sweep(
        name="06_pt_on_canal_flip",
        description="PT: partial X% at contra canal HMA flip (in-profit only).",
        lever="PT",
        angle="L",
        variants=[
            {"label": "25%", "overrides": {"lab_pt_on_canal_flip_pct": 25.0}},
            {"label": "50%", "overrides": {"lab_pt_on_canal_flip_pct": 50.0}},
        ],
    )
    save_result("06_pt_on_canal_flip", payload)
