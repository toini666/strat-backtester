"""H-C1 — `lab_disable_canal_exit_from_hour` : pas de Canal Exit après l'heure X.

Source obs : obs-C1a. MNQ : auto-close profitable à H=18-21 (+$7,367 net AC).
Hypothèse : neutraliser canal_lower/upper (= ±inf) après l'heure X laisse
l'auto-close à 22:00 capturer plus de PnL final.

Sweep : 0 (= V3) → 18, 19, 20, 21.
"""
from __future__ import annotations
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from _shared import run_sweep  # noqa: E402


if __name__ == "__main__":
    rows = run_sweep(
        hypothesis_name="H-C1 lab_disable_canal_exit_from_hour",
        param_key="lab_disable_canal_exit_from_hour",
        off_value=0,
        on_values=[18, 19, 20, 21],
    )
