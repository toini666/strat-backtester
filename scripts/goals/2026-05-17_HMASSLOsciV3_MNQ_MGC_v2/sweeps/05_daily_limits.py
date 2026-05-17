"""Step 5 — daily limits (intra_bar first, after_close fallback)."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _campaign import bench, MNQ_BASE_RISK, MGC_BASE_RISK  # noqa: E402


print("=" * 110)
print("REFERENCE — no daily limit")
print("=" * 110)
bench("no DL", mnq_risk=MNQ_BASE_RISK, mgc_risk=MGC_BASE_RISK)

print()
print("=" * 110)
print("Intra-bar daily limits — loss only")
print("=" * 110)
for loss in (300, 400, 500, 700, 900, 1200, 1500):
    bench(f"intra loss=-{loss}",
          mnq_risk=MNQ_BASE_RISK, mgc_risk=MGC_BASE_RISK,
          daily_loss=loss, daily_limit_mode="intra_bar")

print()
print("=" * 110)
print("Intra-bar daily limits — win only")
print("=" * 110)
for win in (300, 500, 700, 1000, 1500):
    bench(f"intra win=+{win}",
          mnq_risk=MNQ_BASE_RISK, mgc_risk=MGC_BASE_RISK,
          daily_win=win, daily_limit_mode="intra_bar")

print()
print("=" * 110)
print("Intra-bar daily limits — combo")
print("=" * 110)
for w, l in [(500, 500), (500, 700), (700, 700), (1000, 1000)]:
    bench(f"intra win=+{w}/loss=-{l}",
          mnq_risk=MNQ_BASE_RISK, mgc_risk=MGC_BASE_RISK,
          daily_win=w, daily_loss=l, daily_limit_mode="intra_bar")

print()
print("=" * 110)
print("After-close daily limits — loss only")
print("=" * 110)
for loss in (300, 500, 700, 1000):
    bench(f"after loss=-{loss}",
          mnq_risk=MNQ_BASE_RISK, mgc_risk=MGC_BASE_RISK,
          daily_loss=loss, daily_limit_mode="after_close")
