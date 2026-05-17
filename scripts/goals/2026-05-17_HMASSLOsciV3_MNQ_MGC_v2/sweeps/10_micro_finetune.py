"""Step 10 — micro finetune around the best frontier from step 09.

Best so far:
  M0.88/G1.00 mf37 cd2 +BO5,6 → PnL $101,596 / DD $2,039 (DD over by $39)
  M0.82/G1.00 mf39 cd2 +BO5   → PnL $101,390 / DD $2,012 (DD over by $12)
  M0.85/G1.00 mf37 cd2 +BO5,6 → PnL $99,661  / DD $1,961 (PnL under by $339)

Plan: fine M-scale grid (0.83-0.90, step 0.01), test mf=37 & 39, BO[5] vs BO[5,6].
Also test if adding MGC BO[15] or [17] (loser MGC hours) breaks more DD floor.
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


MNQ_E_BO5 = _add_bos(base_engine_mnq(), [5])
MNQ_E_BO56 = _add_bos(base_engine_mnq(), [5, 6])
MNQ_E_BO356 = _add_bos(base_engine_mnq(), [3, 5, 6])
MGC_BASE = base_engine_mgc()
MGC_BO15 = _add_bos(base_engine_mgc(), [15])
MGC_BO17 = _add_bos(base_engine_mgc(), [17])

print()
print("=" * 110)
print("Fine M-scale × {mf=37,39} × {BO5, BO5,6} grid with MGC cd2")
print("=" * 110)
for ms in [0.83, 0.84, 0.85, 0.86, 0.87, 0.88, 0.89, 0.90]:
    for mf in [37, 39]:
        for label, eng in [("BO5", MNQ_E_BO5), ("BO5,6", MNQ_E_BO56)]:
            bench(f"M{ms:.2f}/G1.00 mf{mf} cd2 +{label}",
                  mnq_engine=eng,
                  mnq_params={"mf_length": mf},
                  mgc_params={"cooldown_bars": 2},
                  mnq_risk=MNQ_BASE_RISK * ms, mgc_risk=MGC_BASE_RISK)

print()
print("=" * 110)
print("Try MGC BO[15] or [17] on the best M base")
print("=" * 110)
for ms in [0.85, 0.88, 0.90]:
    for mf in [37, 39]:
        for label, mgc_eng in [("MGC+BO15", MGC_BO15), ("MGC+BO17", MGC_BO17)]:
            bench(f"M{ms:.2f}/G1.00 mf{mf} cd2 +BO5,6 +{label}",
                  mnq_engine=MNQ_E_BO56,
                  mgc_engine=mgc_eng,
                  mnq_params={"mf_length": mf},
                  mgc_params={"cooldown_bars": 2},
                  mnq_risk=MNQ_BASE_RISK * ms, mgc_risk=MGC_BASE_RISK)

print()
print("=" * 110)
print("Try +BO[3,5,6] (DD-window heavy hours) with mf=37,39 cd2")
print("=" * 110)
for ms in [0.85, 0.88, 0.90, 0.95]:
    for mf in [37, 39]:
        bench(f"M{ms:.2f}/G1.00 mf{mf} cd2 +BO3,5,6",
              mnq_engine=MNQ_E_BO356,
              mnq_params={"mf_length": mf},
              mgc_params={"cooldown_bars": 2},
              mnq_risk=MNQ_BASE_RISK * ms, mgc_risk=MGC_BASE_RISK)

print()
print("=" * 110)
print("Try MGC cd=3 with M0.88-0.95 + BO5,6 + mf37/39")
print("=" * 110)
for ms in [0.88, 0.90, 0.92, 0.95]:
    for mf in [37, 39]:
        for cd in [3, 4]:
            bench(f"M{ms:.2f}/G1.00 mf{mf} MGCcd{cd} +BO5,6",
                  mnq_engine=MNQ_E_BO56,
                  mnq_params={"mf_length": mf},
                  mgc_params={"cooldown_bars": cd},
                  mnq_risk=MNQ_BASE_RISK * ms, mgc_risk=MGC_BASE_RISK)
