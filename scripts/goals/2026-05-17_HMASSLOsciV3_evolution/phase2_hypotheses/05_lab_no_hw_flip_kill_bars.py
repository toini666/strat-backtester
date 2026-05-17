"""H-B2 — `lab_no_hw_flip_kill_bars` : defensive exit si pas de HW favorable.

Source obs : obs-B1a/B1b/B1c. 39% des SL MNQ arrivent en ≤3 bars (38% du
SL loss total). Shadow-HW médian 2 bars sur SL vs 3-4 sur Canal Exit.

Mécanisme : à bar entry+N, si AUCUN HW cross favorable dans [entry+1..entry+N],
on injecte `fast_hma_exit_long/short` qui arme `pending_final_exit`. Le
simulateur ferme alors sur le prochain HW cross.

Sweep : 0 (= V3) → 3, 4, 5, 6, 8 bars.
"""
from __future__ import annotations
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from _shared import run_sweep  # noqa: E402


if __name__ == "__main__":
    rows = run_sweep(
        hypothesis_name="H-B2 lab_no_hw_flip_kill_bars",
        param_key="lab_no_hw_flip_kill_bars",
        off_value=0,
        on_values=[3, 4, 5, 6, 8],
    )
