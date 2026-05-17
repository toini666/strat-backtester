"""H8 — Partial X% once MFE crosses trigger_R.

Sourced from obs-PT.L.1: 15% of losses had MFE >= 1R — fixing 25-50% there
would recover ~$30k of edge.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _runner import sweep, save_result


if __name__ == "__main__":
    payload = sweep(
        name="07_pt_on_mfe_r",
        description="PT: partial X% once MFE >= trigger_R.",
        lever="PT",
        angle="L",
        variants=[
            {"label": "25%@0.5R", "overrides": {"lab_pt_on_mfe_r_pct": 25.0, "lab_pt_on_mfe_r_trigger": 0.5}},
            {"label": "25%@1.0R", "overrides": {"lab_pt_on_mfe_r_pct": 25.0, "lab_pt_on_mfe_r_trigger": 1.0}},
            {"label": "50%@1.0R", "overrides": {"lab_pt_on_mfe_r_pct": 50.0, "lab_pt_on_mfe_r_trigger": 1.0}},
            {"label": "50%@1.5R", "overrides": {"lab_pt_on_mfe_r_pct": 50.0, "lab_pt_on_mfe_r_trigger": 1.5}},
        ],
    )
    save_result("07_pt_on_mfe_r", payload)
