"""H4 — MFE floor: close 100% if MFE crossed trigger_R then retraced to floor_R.

Sourced from obs-EX.L.2: 17.5% of trades give back after MFE >= 0.5R, costing
~$66k total. Strong defensive substrate.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _runner import sweep, save_result


if __name__ == "__main__":
    payload = sweep(
        name="04_ex_mfe_floor",
        description="EX H4: full close once MFE >= trigger_R then retraces to floor_R.",
        lever="EX",
        angle="W+L",
        variants=[
            {"label": "trig1.0_floor0.3", "overrides": {"lab_exit_mfe_floor_r": 0.3, "lab_exit_mfe_floor_trigger_r": 1.0}},
            {"label": "trig1.0_floor0.5", "overrides": {"lab_exit_mfe_floor_r": 0.5, "lab_exit_mfe_floor_trigger_r": 1.0}},
            {"label": "trig1.5_floor0.5", "overrides": {"lab_exit_mfe_floor_r": 0.5, "lab_exit_mfe_floor_trigger_r": 1.5}},
            {"label": "trig1.5_floor1.0", "overrides": {"lab_exit_mfe_floor_r": 1.0, "lab_exit_mfe_floor_trigger_r": 1.5}},
            {"label": "trig2.0_floor1.0", "overrides": {"lab_exit_mfe_floor_r": 1.0, "lab_exit_mfe_floor_trigger_r": 2.0}},
        ],
    )
    save_result("04_ex_mfe_floor", payload)
