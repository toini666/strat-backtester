"""Step 7 — finetune the (MNQ risk, MGC risk, BO) frontier.

Best so far from step 06:
  x0.85 + BO [5]                 PnL=$104,318 DD=$2,174  P/DD=47.98
  x0.80 + BO [5]                 PnL=$101,188 DD=$2,175  P/DD=46.51
  x0.85 (no BO)                  PnL=$104,464 DD=$2,240  P/DD=46.65
  x0.90 + BO [5]                 PnL=$107,860 DD=$2,235  P/DD=48.27
  x0.75 + BO [5,6]               PnL=$ 94,925 DD=$2,017  PnL fails

Hypothesis A: lower MNQ slightly + raise MGC to keep PnL ≥ $100k.
Hypothesis B: keep MNQ baseline blackouts but find the sweet spot risk scale.
"""
from __future__ import annotations

import copy
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _campaign import (  # noqa: E402
    bench, base_engine_mnq, base_engine_mgc, MNQ_BASE_RISK, MGC_BASE_RISK, _bw,
)


def _add_bos(engine, hours):
    e = copy.deepcopy(engine)
    e.blackout_windows = list(e.blackout_windows) + [_bw(True, h, 0, h + 1, 0) for h in hours]
    return e


print("=" * 110)
print("REFERENCE")
print("=" * 110)
bench("baseline (NEW preset)",
      mnq_risk=MNQ_BASE_RISK, mgc_risk=MGC_BASE_RISK)

print()
print("=" * 110)
print("MNQ scale × MGC scale grid (no extra blackouts)")
print("=" * 110)
for ms in [0.75, 0.80, 0.82, 0.85, 0.88]:
    for gs in [0.95, 1.00, 1.05, 1.10, 1.15, 1.20]:
        bench(f"M{ms:.2f}/G{gs:.2f}",
              mnq_risk=MNQ_BASE_RISK * ms, mgc_risk=MGC_BASE_RISK * gs)

print()
print("=" * 110)
print("MNQ scale × MGC scale grid (+ MNQ BO[5])")
print("=" * 110)
for ms in [0.75, 0.80, 0.82, 0.85, 0.88]:
    for gs in [0.95, 1.00, 1.05, 1.10, 1.15, 1.20]:
        bench(f"M{ms:.2f}/G{gs:.2f} +BO5",
              mnq_engine=_add_bos(base_engine_mnq(), [5]),
              mnq_risk=MNQ_BASE_RISK * ms, mgc_risk=MGC_BASE_RISK * gs)

print()
print("=" * 110)
print("MNQ scale × MGC scale grid (+ MNQ BO[5,6])")
print("=" * 110)
for ms in [0.75, 0.78, 0.80, 0.82, 0.85]:
    for gs in [1.00, 1.05, 1.10, 1.15, 1.20]:
        bench(f"M{ms:.2f}/G{gs:.2f} +BO5,6",
              mnq_engine=_add_bos(base_engine_mnq(), [5, 6]),
              mnq_risk=MNQ_BASE_RISK * ms, mgc_risk=MGC_BASE_RISK * gs)
