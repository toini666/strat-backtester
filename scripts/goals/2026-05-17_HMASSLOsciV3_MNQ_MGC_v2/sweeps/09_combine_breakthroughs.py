"""Step 9 — combine the breakthroughs from step 08.

Levers found:
  mf_length=37 (MNQ): DD 2,119 vs base 2,166 (-$47), PnL +$1,534
  MGC cooldown_bars=2: DD 2,125 vs base 2,166 (-$41), PnL -$3,375
  Best blackout: MNQ BO[5] (already applied in base)

Hypothesis: combining mf_length=37 + MGC cooldown=2 stacks => DD<$2,000.
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


MGC_RISK = MGC_BASE_RISK  # 0.52%
MNQ_ENGINE_BO5 = _add_bos(base_engine_mnq(), [5])

print()
print("=" * 110)
print("BASELINE & BEST SINGLES")
print("=" * 110)
bench("base M0.82 +BO5",
      mnq_engine=MNQ_ENGINE_BO5,
      mnq_risk=MNQ_BASE_RISK * 0.82, mgc_risk=MGC_RISK)

bench("base + mf=37",
      mnq_engine=MNQ_ENGINE_BO5,
      mnq_params={"mf_length": 37},
      mnq_risk=MNQ_BASE_RISK * 0.82, mgc_risk=MGC_RISK)

bench("base + MGC cd=2",
      mnq_engine=MNQ_ENGINE_BO5,
      mgc_params={"cooldown_bars": 2},
      mnq_risk=MNQ_BASE_RISK * 0.82, mgc_risk=MGC_RISK)

print()
print("=" * 110)
print("COMBINE — mf=37 + MGC cd=2, vary MNQ risk + MGC risk")
print("=" * 110)
for ms in [0.78, 0.80, 0.82, 0.85, 0.88, 0.90, 0.95, 1.00]:
    for gs in [0.95, 1.00, 1.05]:
        bench(f"M{ms:.2f}/G{gs:.2f} mf37 cd2",
              mnq_engine=MNQ_ENGINE_BO5,
              mnq_params={"mf_length": 37},
              mgc_params={"cooldown_bars": 2},
              mnq_risk=MNQ_BASE_RISK * ms, mgc_risk=MGC_RISK * gs)

print()
print("=" * 110)
print("Same combo, additional MGC cd options")
print("=" * 110)
for cd in [3, 4]:
    for ms in [0.82, 0.85, 0.88]:
        bench(f"M{ms:.2f}/G1.00 mf37 cd={cd}",
              mnq_engine=MNQ_ENGINE_BO5,
              mnq_params={"mf_length": 37},
              mgc_params={"cooldown_bars": cd},
              mnq_risk=MNQ_BASE_RISK * ms, mgc_risk=MGC_RISK)

print()
print("=" * 110)
print("Try +BO[5,6] vs +BO[5] with combined")
print("=" * 110)
MNQ_ENGINE_BO56 = _add_bos(base_engine_mnq(), [5, 6])
for ms in [0.78, 0.82, 0.85, 0.88]:
    bench(f"M{ms:.2f}/G1.00 mf37 cd2 +BO5,6",
          mnq_engine=MNQ_ENGINE_BO56,
          mnq_params={"mf_length": 37},
          mgc_params={"cooldown_bars": 2},
          mnq_risk=MNQ_BASE_RISK * ms, mgc_risk=MGC_RISK)

print()
print("=" * 110)
print("Test other MNQ mf_length around 37 (combined with MGC cd=2)")
print("=" * 110)
for mf in [33, 35, 39, 41, 43]:
    bench(f"M0.82/G1.00 mf{mf} cd2",
          mnq_engine=MNQ_ENGINE_BO5,
          mnq_params={"mf_length": mf},
          mgc_params={"cooldown_bars": 2},
          mnq_risk=MNQ_BASE_RISK * 0.82, mgc_risk=MGC_RISK)
