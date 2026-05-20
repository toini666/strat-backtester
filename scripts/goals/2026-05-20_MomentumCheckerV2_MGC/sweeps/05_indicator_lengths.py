"""Phase 5 — Indicator lengths sweep.

Scans each indicator's length parameter around the V1-compat baseline.
This is where MNQ campaign found its top single-lever win (amp_mult 2.5→3.5).
For MGC, the baseline amp_mult is 2.0 (vs MNQ's 2.5), so the optimal
likely lives in a different range.

Baseline (V1-compat): PnL=$49,733 / $DD=$3,655 / N=785 / WR=40.1%
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

CAMPAIGN_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CAMPAIGN_DIR / "sweeps"))

from scripts.goals._shared.harness import bench  # noqa: E402

from _campaign import (  # noqa: E402
    END,
    INITIAL_EQUITY,
    INTERVAL,
    MAX_CONTRACTS,
    RISK_PER_TRADE,
    START,
    STRATEGY,
    SYMBOL,
    V1_COMPAT_PARAMS,
    anchor_engine,
)


def _common():
    return dict(
        strategy_name=STRATEGY,
        symbol=SYMBOL,
        interval=INTERVAL,
        start=START,
        end=END,
        initial_equity=INITIAL_EQUITY,
        risk_per_trade=RISK_PER_TRADE,
        max_contracts=MAX_CONTRACTS,
        engine_settings=anchor_engine(),
    )


def main() -> int:
    print("=" * 110)
    print(f"PHASE 5 — Indicator lengths  |  {STRATEGY}  {SYMBOL} {INTERVAL}  risk={RISK_PER_TRADE*100:.2f}%")
    print(f"Baseline (V1-compat): PnL=$49,733  $DD=$3,655  N=785")
    print("=" * 110)

    t0 = time.time()
    n = 0

    # Oscillator: hyper_wave_length, signal_length, mf_length, mf_smooth
    print("\n--- 1) Oscillator lengths ---")
    for hwl in (3, 5, 7):
        p = dict(V1_COMPAT_PARAMS); p["hyper_wave_length"] = hwl
        bench(f"hyper_wave_length={hwl}", strategy_params=p, **_common()); n += 1
    for sl in (2, 3, 5):
        p = dict(V1_COMPAT_PARAMS); p["signal_length"] = sl
        bench(f"signal_length={sl}", strategy_params=p, **_common()); n += 1
    for mfl in (25, 30, 35, 40, 50):
        p = dict(V1_COMPAT_PARAMS); p["mf_length"] = mfl
        bench(f"mf_length={mfl}", strategy_params=p, **_common()); n += 1
    for mfs in (3, 5, 6, 8):
        p = dict(V1_COMPAT_PARAMS); p["mf_smooth"] = mfs
        bench(f"mf_smooth={mfs}", strategy_params=p, **_common()); n += 1

    # 2) EMA lengths
    print("\n--- 2) EMA lengths ---")
    for ep in (20, 30, 40, 50):
        p = dict(V1_COMPAT_PARAMS); p["ema_prin_len"] = ep
        bench(f"ema_prin_len={ep}", strategy_params=p, **_common()); n += 1
    for es in (5, 9, 13, 20):
        p = dict(V1_COMPAT_PARAMS); p["ema_sec_len"] = es
        bench(f"ema_sec_len={es}", strategy_params=p, **_common()); n += 1

    # 3) Supertrend
    print("\n--- 3) Supertrend ---")
    for sa in (7, 10, 14, 21):
        p = dict(V1_COMPAT_PARAMS); p["st_atr"] = sa
        bench(f"st_atr={sa}", strategy_params=p, **_common()); n += 1
    for sm in (2.0, 2.5, 3.0, 3.5, 4.0):
        p = dict(V1_COMPAT_PARAMS); p["st_mult"] = sm
        bench(f"st_mult={sm}", strategy_params=p, **_common()); n += 1

    # 4) Alligator (around standard 13/8/5)
    print("\n--- 4) Alligator ---")
    for jaw, teeth, lips in [(13, 8, 5), (21, 13, 8), (8, 5, 3)]:
        p = dict(V1_COMPAT_PARAMS)
        p["jaw_length"] = jaw; p["teeth_length"] = teeth; p["lips_length"] = lips
        bench(f"alligator={jaw}/{teeth}/{lips}", strategy_params=p, **_common()); n += 1

    # 5) STC
    print("\n--- 5) STC ---")
    for sl_ in (8, 10, 12, 16):
        p = dict(V1_COMPAT_PARAMS); p["stc_length"] = sl_
        bench(f"stc_length={sl_}", strategy_params=p, **_common()); n += 1
    for fl, sl_ in [(23, 50), (26, 50), (32, 50), (26, 60), (32, 60)]:
        p = dict(V1_COMPAT_PARAMS); p["stc_fast_len"] = fl; p["stc_slow_len"] = sl_
        bench(f"stc_fast/slow={fl}/{sl_}", strategy_params=p, **_common()); n += 1

    # 6) HMA — amp_mult is critical (MNQ found 3.5 vs 2.5)
    print("\n--- 6) HMA ribbon: amp_mult & lengths ---")
    for am in (1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5):
        p = dict(V1_COMPAT_PARAMS); p["amp_mult"] = am
        bench(f"amp_mult={am}", strategy_params=p, **_common()); n += 1
    for h1, h2 in [(21, 42), (42, 84), (63, 126)]:
        p = dict(V1_COMPAT_PARAMS); p["hma1_len"] = h1; p["hma2_len"] = h2
        bench(f"hma1/hma2={h1}/{h2}", strategy_params=p, **_common()); n += 1
    for hel in (5, 7, 9):
        p = dict(V1_COMPAT_PARAMS); p["hma_ema_len"] = hel
        bench(f"hma_ema_len={hel}", strategy_params=p, **_common()); n += 1

    elapsed = time.time() - t0
    print(f"\nTotal sims: {n}  |  Elapsed: {elapsed:.1f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
