"""H-A3 — `lab_min_sl_points` : filtre minimum distance SL (refuse SL trop tight).

Source obs : obs-A2a (ambigu — small SL trades ont WR 36% MNQ mais +$36k PnL via taille).
Hypothèse à tester pour répondre : la stabilité (réduction DD) compense-t-elle la perte PnL ?

Sweep : 0 (= V3) → 5, 10, 15, 20, 30 points.
"""
from __future__ import annotations
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from _shared import run_sweep  # noqa: E402


if __name__ == "__main__":
    rows = run_sweep(
        hypothesis_name="H-A3 lab_min_sl_points",
        param_key="lab_min_sl_points",
        off_value=0.0,
        on_values=[5.0, 10.0, 15.0, 20.0, 30.0],
    )
