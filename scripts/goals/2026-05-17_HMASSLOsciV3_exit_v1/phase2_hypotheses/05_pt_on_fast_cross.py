"""H5/H6 — Partial X% at fast HMA cross (in-profit only via simulator gate).

Sourced from obs-EX.W.1 / PT.W.1: 65% of setups have fast cross in profit;
locking 25/50/75% there fixes ~$28k without harming tail.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _runner import sweep, save_result


if __name__ == "__main__":
    payload = sweep(
        name="05_pt_on_fast_cross",
        description="PT: partial X% at fast HMA cross (in-profit only).",
        lever="PT",
        angle="W",
        variants=[
            {"label": "25%", "overrides": {"lab_pt_on_fast_cross_pct": 25.0}},
            {"label": "50%", "overrides": {"lab_pt_on_fast_cross_pct": 50.0}},
            {"label": "75%", "overrides": {"lab_pt_on_fast_cross_pct": 75.0}},
        ],
    )
    save_result("05_pt_on_fast_cross", payload)
