"""Step 1 — baseline replay of the 'Multi-Asset — MNQ/MGC - NEW' preset."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _campaign import bench, MNQ_BASE_RISK, MGC_BASE_RISK, DD_BUDGET, PNL_TARGET  # noqa: E402

print(f"Goal: PnL > ${PNL_TARGET:,.0f} & DD < ${DD_BUDGET:,.0f}\n")

bench("baseline NEW preset (mnq=0.48%, mgc=0.52%)",
      mnq_risk=MNQ_BASE_RISK, mgc_risk=MGC_BASE_RISK)
