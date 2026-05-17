"""Step 4 — single-hour blackouts on each leg, candidates from step 3.

MNQ candidates (global loss hours not yet blocked):
  - H=6  (-$2,230, N=49) ← biggest global loser
  - H=4  (-$663,  N=53)
  - H=13 (-$2,689 in baseline w/o h13 BO; was in old winner)
  - H=0  (DD-window loser)
  - H=3,5 (DD-window losers)

MGC candidates:
  - H=17 (-$1,002, N=54)
  - H=20 (-$195,  N=39)
  - H=21 (-$299,  N=43)
  - H=14 (DD-window loser)
"""
from __future__ import annotations

import copy
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _campaign import (  # noqa: E402
    bench, base_engine_mnq, base_engine_mgc, MNQ_BASE_RISK, MGC_BASE_RISK, _bw,
)


def _add_bo(engine, start_hour, end_hour):
    """Append an active 1-hour blackout to a clone of `engine`."""
    e = copy.deepcopy(engine)
    e.blackout_windows = list(e.blackout_windows) + [_bw(True, start_hour, 0, end_hour, 0)]
    return e


# --- baseline reference ---
print("=" * 110)
print("REFERENCE")
print("=" * 110)
bench("baseline (NEW preset)",
      mnq_risk=MNQ_BASE_RISK, mgc_risk=MGC_BASE_RISK)

# --- single MNQ blackout candidates ---
print()
print("=" * 110)
print("MNQ — single blackout sweep (MGC unchanged)")
print("=" * 110)
mnq_hours = [0, 3, 4, 5, 6, 13, 16, 17, 18, 19, 20]
for h in mnq_hours:
    bench(f"MNQ +BO {h:02d}-{h+1:02d}",
          mnq_engine=_add_bo(base_engine_mnq(), h, h + 1),
          mnq_risk=MNQ_BASE_RISK, mgc_risk=MGC_BASE_RISK)

# --- single MGC blackout candidates ---
print()
print("=" * 110)
print("MGC — single blackout sweep (MNQ unchanged)")
print("=" * 110)
mgc_hours = [10, 13, 14, 15, 16, 17, 18, 20, 21]
for h in mgc_hours:
    bench(f"MGC +BO {h:02d}-{h+1:02d}",
          mgc_engine=_add_bo(base_engine_mgc(), h, h + 1),
          mnq_risk=MNQ_BASE_RISK, mgc_risk=MGC_BASE_RISK)
