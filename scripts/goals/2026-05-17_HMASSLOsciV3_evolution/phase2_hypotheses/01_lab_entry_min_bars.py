"""H-A1 — `lab_entry_min_bars` : refuser les entrées trop précoces dans la fenêtre.

Source obs : obs-A1a. WR à bar 3 = 65% (MGC) / 55% (MNQ) vs ~48-54% à bar 0.

Sweep : 0 (= V3) → 1, 2, 3, 4.
"""
from __future__ import annotations
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from _shared import run_sweep  # noqa: E402


if __name__ == "__main__":
    rows = run_sweep(
        hypothesis_name="H-A1 lab_entry_min_bars",
        param_key="lab_entry_min_bars",
        off_value=0,
        on_values=[1, 2, 3, 4],
    )
