"""Step 11 — last targeted probe to break the $2,009 DD floor.

INTERRUPTED — user stopped the campaign before this sweep completed.
Only the baseline run actually executed. Sweep design preserved for future runs.

Best valid so far: M0.86/G1.00 mf=37 cd2 +BO5,6 → PnL $100,076 / DD $2,009

Test 1-D variations on unexplored axes (any might shift one trade across
contract-floor rounding and break the step):
  - MNQ mf_smooth: 5, 6, 8, 9 (base=7)
  - MNQ signal_length: 3, 5, 6 (base=4)
  - MNQ hyper_wave_length: 5, 6, 8, 9 (base=7)
  - MNQ entry_window_bars: 2, 4 (base=3)
  - MGC mf_length: 25, 27, 31, 33 (base=29)
  - MGC mf_smooth: 4, 6, 7 (base=5)
  - MGC signal_length: 4, 5 (base=3)
  - MGC hyper_wave_length: 4, 6, 7 (base=5)
  - MGC entry_window_bars: 3, 4, 6, 7 (base=5)
  - Fractional MGC risk scale: 0.96, 0.97, 0.98, 0.99, 1.01, 1.02 (might shift one rounding step)
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


MNQ_E_BO56 = _add_bos(base_engine_mnq(), [5, 6])

BASE_KW = dict(
    mnq_engine=MNQ_E_BO56,
    mnq_params={"mf_length": 37},
    mgc_params={"cooldown_bars": 2},
    mnq_risk=MNQ_BASE_RISK * 0.86,
    mgc_risk=MGC_BASE_RISK,
)


def with_mnq(extra):
    kw = dict(BASE_KW)
    kw["mnq_params"] = {**kw["mnq_params"], **extra}
    return kw


def with_mgc(extra):
    kw = dict(BASE_KW)
    kw["mgc_params"] = {**kw["mgc_params"], **extra}
    return kw


print("=" * 110)
print("BASELINE")
print("=" * 110)
bench("base (M0.86 mf37 cd2 +BO5,6)", **BASE_KW)

print()
print("=" * 110)
print("MNQ mf_smooth sweep (base=7)")
print("=" * 110)
for ms in [5, 6, 8, 9]:
    bench(f"MNQ mf_smooth={ms}", **with_mnq({"mf_smooth": ms}))

print()
print("=" * 110)
print("MNQ signal_length sweep (base=4)")
print("=" * 110)
for s in [3, 5, 6]:
    bench(f"MNQ signal_length={s}", **with_mnq({"signal_length": s}))

print()
print("=" * 110)
print("MNQ hyper_wave_length sweep (base=7)")
print("=" * 110)
for h in [5, 6, 8, 9]:
    bench(f"MNQ hyper_wave_length={h}", **with_mnq({"hyper_wave_length": h}))

print()
print("=" * 110)
print("MNQ entry_window_bars sweep (base=3)")
print("=" * 110)
for ew in [2, 4]:
    bench(f"MNQ entry_window_bars={ew}", **with_mnq({"entry_window_bars": ew}))

print()
print("=" * 110)
print("MGC mf_length sweep (base=29)")
print("=" * 110)
for mf in [25, 27, 31, 33]:
    bench(f"MGC mf_length={mf}", **with_mgc({"mf_length": mf}))

print()
print("=" * 110)
print("MGC mf_smooth sweep (base=5)")
print("=" * 110)
for ms in [4, 6, 7]:
    bench(f"MGC mf_smooth={ms}", **with_mgc({"mf_smooth": ms}))

print()
print("=" * 110)
print("MGC signal_length sweep (base=3)")
print("=" * 110)
for s in [4, 5]:
    bench(f"MGC signal_length={s}", **with_mgc({"signal_length": s}))

print()
print("=" * 110)
print("MGC hyper_wave_length sweep (base=5)")
print("=" * 110)
for h in [4, 6, 7]:
    bench(f"MGC hyper_wave_length={h}", **with_mgc({"hyper_wave_length": h}))

print()
print("=" * 110)
print("MGC entry_window_bars sweep (base=5)")
print("=" * 110)
for ew in [3, 4, 6, 7]:
    bench(f"MGC entry_window_bars={ew}", **with_mgc({"entry_window_bars": ew}))

print()
print("=" * 110)
print("Fractional MGC risk sweep")
print("=" * 110)
for gs in [0.96, 0.97, 0.98, 0.99, 1.01, 1.02]:
    kw = dict(BASE_KW)
    kw["mgc_risk"] = MGC_BASE_RISK * gs
    bench(f"MGC risk x{gs:.2f}", **kw)
