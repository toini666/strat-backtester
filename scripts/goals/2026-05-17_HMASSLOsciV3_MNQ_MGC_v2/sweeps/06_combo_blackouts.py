"""Step 6 — combo blackouts + asymmetric risk.

Best singles:
  MNQ H=5  -> DD 2,560 (-137 vs base), PnL 113,155
  MNQ H=6  -> DD 2,618 (-79),  PnL 113,069
  MGC H=15 -> DD 2,552 (-145), PnL 110,236 (heavy PnL cost)
  MGC H=20 -> DD 2,693 (-4),   PnL 113,602 (slightly +PnL!)
  MGC H=21 -> DD 2,695 (-2),   PnL 113,415

MNQ dominates DD ($-1,893 in worst window vs MGC $-538), so lowering MNQ risk
is the main lever along with combo blackouts.
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
bench("baseline (NEW preset)", mnq_risk=MNQ_BASE_RISK, mgc_risk=MGC_BASE_RISK)

# ---- MNQ blackout combos ----
print()
print("=" * 110)
print("MNQ multi-blackout combos (MGC unchanged)")
print("=" * 110)
mnq_combos = [
    [5],
    [6],
    [5, 6],
    [5, 6, 19],
    [5, 6, 20],
    [5, 19],
    [5, 20],
    [3, 5, 6],
    [5, 6, 13],         # 13 was in previous winner, hurt DD alone but maybe in combo it lifts the floor
]
for hours in mnq_combos:
    bench(f"MNQ +BO {hours}",
          mnq_engine=_add_bos(base_engine_mnq(), hours),
          mnq_risk=MNQ_BASE_RISK, mgc_risk=MGC_BASE_RISK)

# ---- MGC blackout combos (focus on small-impact additions) ----
print()
print("=" * 110)
print("MGC multi-blackout combos (MNQ unchanged)")
print("=" * 110)
mgc_combos = [
    [15],
    [15, 20],
    [15, 21],
    [20, 21],
    [15, 20, 21],
    [16, 20],
]
for hours in mgc_combos:
    bench(f"MGC +BO {hours}",
          mgc_engine=_add_bos(base_engine_mgc(), hours),
          mnq_risk=MNQ_BASE_RISK, mgc_risk=MGC_BASE_RISK)

# ---- Cross combos: best MNQ + best MGC ----
print()
print("=" * 110)
print("Cross combos (best MNQ + best MGC blackouts)")
print("=" * 110)
for m_hrs in [[5, 6], [5, 6, 19], [5, 6, 13]]:
    for g_hrs in [[15], [20, 21], [15, 20, 21], []]:
        bench(f"MNQ {m_hrs} + MGC {g_hrs}",
              mnq_engine=_add_bos(base_engine_mnq(), m_hrs),
              mgc_engine=_add_bos(base_engine_mgc(), g_hrs),
              mnq_risk=MNQ_BASE_RISK, mgc_risk=MGC_BASE_RISK)

# ---- MNQ risk reduction (MNQ dominates DD) ----
print()
print("=" * 110)
print("MNQ risk reduction alone (no extra blackouts)")
print("=" * 110)
for s in [0.70, 0.75, 0.80, 0.85, 0.90, 0.95]:
    bench(f"MNQ x{s:.2f}",
          mnq_risk=MNQ_BASE_RISK * s, mgc_risk=MGC_BASE_RISK)

# ---- MNQ risk reduction + best MNQ blackouts ----
print()
print("=" * 110)
print("MNQ risk × MNQ blackouts (combo)")
print("=" * 110)
for s in [0.75, 0.80, 0.85, 0.90]:
    for m_hrs in [[5], [5, 6], [5, 6, 19]]:
        bench(f"MNQ x{s:.2f} + BO {m_hrs}",
              mnq_engine=_add_bos(base_engine_mnq(), m_hrs),
              mnq_risk=MNQ_BASE_RISK * s, mgc_risk=MGC_BASE_RISK)
