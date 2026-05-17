"""Step 2 — 1-D risk sweep on each leg, keeping the other at baseline."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _campaign import bench, MNQ_BASE_RISK, MGC_BASE_RISK  # noqa: E402

scales = [0.50, 0.60, 0.70, 0.75, 0.80, 0.85, 0.90, 0.95, 1.00, 1.05, 1.10]

print("=" * 110)
print(f"MNQ risk sweep (MGC fixed at {MGC_BASE_RISK*100:.2f}%)")
print("=" * 110)
for s in scales:
    r = MNQ_BASE_RISK * s
    bench(f"MNQ x{s:.2f} = {r*100:.4f}%",
          mnq_risk=r, mgc_risk=MGC_BASE_RISK)

print()
print("=" * 110)
print(f"MGC risk sweep (MNQ fixed at {MNQ_BASE_RISK*100:.2f}%)")
print("=" * 110)
for s in scales:
    r = MGC_BASE_RISK * s
    bench(f"MGC x{s:.2f} = {r*100:.4f}%",
          mnq_risk=MNQ_BASE_RISK, mgc_risk=r)

print()
print("=" * 110)
print("Symmetric scale (both legs)")
print("=" * 110)
for s in [0.70, 0.75, 0.80, 0.85, 0.90, 0.95]:
    bench(f"BOTH x{s:.2f}",
          mnq_risk=MNQ_BASE_RISK * s, mgc_risk=MGC_BASE_RISK * s)
