"""Phase 3 — finer H6 sweep + combo exploration.

H6 (partial at fast cross) was the only sweep producing a positive PnL delta
(MNQ 25% → +$1,225 but DD inflated +$1,429). This file:
  1. Tests finer percentages (10%, 15%, 20%) to find a less-DD-hostile sweet spot.
  2. Tests combos of the least-bad hypotheses to see if interactions yield a winner.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "phase2_hypotheses"))

from _runner import sweep, save_result


if __name__ == "__main__":
    # 1. Finer H6 sweep on both presets
    payload1 = sweep(
        name="P3_01a_h6_fine",
        description="Phase3: finer H6 partial at fast cross — find lower-DD sweet spot.",
        lever="PT",
        angle="W",
        variants=[
            {"label": "10%", "overrides": {"lab_pt_on_fast_cross_pct": 10.0}},
            {"label": "15%", "overrides": {"lab_pt_on_fast_cross_pct": 15.0}},
            {"label": "20%", "overrides": {"lab_pt_on_fast_cross_pct": 20.0}},
        ],
    )
    save_result("P3_01a_h6_fine", payload1)

    # 2. Combo: H6 25% + H8 50%@1.5R (both lock-in-profit at different stages)
    payload2 = sweep(
        name="P3_01b_combo_h6_h8",
        description="Phase3: combo — H6 partial at fast cross + H8 partial at MFE seuil.",
        lever="PT",
        angle="W+L",
        variants=[
            {"label": "h6=25_h8=50@1.5", "overrides": {
                "lab_pt_on_fast_cross_pct": 25.0,
                "lab_pt_on_mfe_r_pct": 50.0,
                "lab_pt_on_mfe_r_trigger": 1.5,
            }},
            {"label": "h6=15_h8=50@1.5", "overrides": {
                "lab_pt_on_fast_cross_pct": 15.0,
                "lab_pt_on_mfe_r_pct": 50.0,
                "lab_pt_on_mfe_r_trigger": 1.5,
            }},
        ],
    )
    save_result("P3_01b_combo_h6_h8", payload2)
