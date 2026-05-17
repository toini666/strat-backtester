"""H-B1 — `lab_max_2bar_body_pct` : filtre 2-bar cumulative body.

Source obs : obs-B1d. Hypothèse faible a priori — l'observation Phase 1
montre que les candles agressives ont MEILLEUR WR. Mais le 2-bar cumulé
pourrait capter un pattern différent (entrée après un swing déjà épuisé).

Sweep : 0 (= V3) → 0.5, 0.7, 1.0, 1.5 %.
"""
from __future__ import annotations
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from _shared import run_sweep  # noqa: E402


if __name__ == "__main__":
    rows = run_sweep(
        hypothesis_name="H-B1 lab_max_2bar_body_pct",
        param_key="lab_max_2bar_body_pct",
        off_value=0.0,
        on_values=[0.5, 0.7, 1.0, 1.5],
    )
