"""Step 8 — strategy params + daily limits, on the best risk-scaled config.

Best so far: M0.82/G1.00 + BO[5] → PnL $104,044 / DD $2,166 (margin DD = -$166).

Floor at ~$2,150 looks like contract-floor + structural DD window. Try to break it via:
 1. max_sl_points tightening on MNQ (300 → 250/200/150/100) — caps per-trade loss
 2. cooldown_bars MNQ (3 → 4/5/6) — fewer entries inside DD windows
 3. mf_length / mf_smooth MNQ — different signal mix
 4. sig_extreme MNQ (40 → 35/45/50) — entry filter
 5. Daily limits in intra_bar mode (sometimes useful for cluster-DD)
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


MNQ_RISK = MNQ_BASE_RISK * 0.82  # 0.3936%
MGC_RISK = MGC_BASE_RISK * 1.00  # 0.52%
MNQ_ENGINE_BO5 = _add_bos(base_engine_mnq(), [5])

print(f"BASE: MNQ risk={MNQ_RISK*100:.4f}% + BO[5], MGC risk={MGC_RISK*100:.4f}%")
print()
print("=" * 110)
print("REFERENCE")
print("=" * 110)
bench("base M0.82/G1.00 +BO5",
      mnq_engine=MNQ_ENGINE_BO5,
      mnq_risk=MNQ_RISK, mgc_risk=MGC_RISK)

print()
print("=" * 110)
print("MNQ max_sl_points sweep")
print("=" * 110)
for sl in [100, 150, 200, 250, 350]:
    bench(f"MNQ max_sl_points={sl}",
          mnq_engine=MNQ_ENGINE_BO5,
          mnq_params={"max_sl_points": sl},
          mnq_risk=MNQ_RISK, mgc_risk=MGC_RISK)

print()
print("=" * 110)
print("MNQ cooldown_bars sweep")
print("=" * 110)
for cd in [2, 4, 5, 6, 8]:
    bench(f"MNQ cooldown_bars={cd}",
          mnq_engine=MNQ_ENGINE_BO5,
          mnq_params={"cooldown_bars": cd},
          mnq_risk=MNQ_RISK, mgc_risk=MGC_RISK)

print()
print("=" * 110)
print("MNQ mf_length sweep")
print("=" * 110)
for mf in [25, 27, 29, 33, 35, 37]:
    bench(f"MNQ mf_length={mf}",
          mnq_engine=MNQ_ENGINE_BO5,
          mnq_params={"mf_length": mf},
          mnq_risk=MNQ_RISK, mgc_risk=MGC_RISK)

print()
print("=" * 110)
print("MNQ sig_extreme sweep")
print("=" * 110)
for s in [30, 35, 45, 50, 55]:
    bench(f"MNQ sig_extreme={s}",
          mnq_engine=MNQ_ENGINE_BO5,
          mnq_params={"sig_extreme": s},
          mnq_risk=MNQ_RISK, mgc_risk=MGC_RISK)

print()
print("=" * 110)
print("MGC max_sl_points sweep")
print("=" * 110)
for sl in [60, 80, 120, 150]:
    bench(f"MGC max_sl_points={sl}",
          mnq_engine=MNQ_ENGINE_BO5,
          mgc_params={"max_sl_points": sl},
          mnq_risk=MNQ_RISK, mgc_risk=MGC_RISK)

print()
print("=" * 110)
print("MGC cooldown_bars sweep")
print("=" * 110)
for cd in [2, 3, 4, 5]:
    bench(f"MGC cooldown_bars={cd}",
          mnq_engine=MNQ_ENGINE_BO5,
          mgc_params={"cooldown_bars": cd},
          mnq_risk=MNQ_RISK, mgc_risk=MGC_RISK)

print()
print("=" * 110)
print("Daily limits — intra_bar")
print("=" * 110)
for loss in [300, 500, 700, 1000, 1500]:
    bench(f"intra loss=-{loss}",
          mnq_engine=MNQ_ENGINE_BO5,
          mnq_risk=MNQ_RISK, mgc_risk=MGC_RISK,
          daily_loss=loss, daily_limit_mode="intra_bar")
for win in [500, 800, 1200, 1800]:
    bench(f"intra win=+{win}",
          mnq_engine=MNQ_ENGINE_BO5,
          mnq_risk=MNQ_RISK, mgc_risk=MGC_RISK,
          daily_win=win, daily_limit_mode="intra_bar")
for w, l in [(500, 500), (700, 700), (800, 700), (1000, 1000)]:
    bench(f"intra win=+{w}/loss=-{l}",
          mnq_engine=MNQ_ENGINE_BO5,
          mnq_risk=MNQ_RISK, mgc_risk=MGC_RISK,
          daily_win=w, daily_loss=l, daily_limit_mode="intra_bar")
