"""Phase 8b — Surgical blackouts + alternative compositions.

Hour bucket without blackouts revealed:
  - H=12: -$1,758 (22% WR)  [V1 covers via 12:30-14, but H=12:00-12:30 leaks]
  - H=13: -$651  (35% WR)   [V1 covers]
  - H=15: -$428  (40% WR)   [open]
  - H=18: -$611  (52% WR)   [V1 covers via 17-21]
  - H=20: -$925  (45% WR)   [V1 covers]
  - H=23: -$2,512 (8% WR)   [22-23:59 BO but leaks via DST/timing]

The V1 evening BO (17-21) cuts both profitable (H=17 $1,338, H=19 $752,
H=21 $1,157) AND lossy (H=18 -$611, H=20 -$925) hours. A surgical version
might keep more of the profitable trades.

Tests:
  1. Drop the 17-21 blackout entirely, replace with surgical 18-19 and 20-21.
  2. Tighten the lunch BO from 12:30 to 12:00 (catch H=12 leak).
  3. Add 15:00-16:00 to remove the lossy hour.
  4. Stretch 22-23:59 to 21:00-23:59 to catch H=23 DST leak.
  5. Combine the best blackouts with NOBE + master combo.
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
    START,
    STRATEGY,
    SYMBOL,
    V1_COMPAT_PARAMS,
    build_engine,
)


MASTER_NOBE = {
    **V1_COMPAT_PARAMS,
    "pts_hma_slow":     1,
    "hma_window_bars":  5,
    "max_candle_pct":   0.3,
    "ema_sec_len":      5,
    "be_at_rr":         0.0,    # drop E
    "sl_max_points":    100.0,
}


def _common(risk, engine, params):
    return dict(
        strategy_name=STRATEGY,
        symbol=SYMBOL,
        interval=INTERVAL,
        start=START,
        end=END,
        initial_equity=INITIAL_EQUITY,
        risk_per_trade=risk,
        max_contracts=MAX_CONTRACTS,
        engine_settings=engine,
        strategy_params=params,
    )


def main() -> int:
    print("=" * 110)
    print(f"PHASE 8b — Surgical blackouts  |  {STRATEGY}  {SYMBOL} {INTERVAL}")
    print(f"Combo: MASTER_NOBE (without be_at_rr)")
    print("=" * 110)

    t0 = time.time()
    n = 0

    # Define candidate blackout configs
    BO = {
        "V1_anchor":         [(12, 30, 14, 0), (17, 0, 21, 0)],
        # Try cutting the H=12 leak
        "V1+lunch_widen":    [(12, 0, 14, 0), (17, 0, 21, 0)],
        # Surgical: only the lossy hours of US session
        "Lunch + 18,20":     [(12, 30, 14, 0), (18, 0, 19, 0), (20, 0, 21, 0)],
        # Lunch + 20-21 only (keep H=17,18,19)
        "Lunch + 20-21":     [(12, 30, 14, 0), (20, 0, 21, 0)],
        # Lunch + 18-19, 20-21
        "Lunch + 18-19,20-21": [(12, 30, 14, 0), (18, 0, 19, 0), (20, 0, 21, 0)],
        # Lunch + 15 + 18-19, 20-21 (also cut H=15)
        "Lunch + 15-16 + 18-19,20-21": [
            (12, 30, 14, 0), (15, 0, 16, 0), (18, 0, 19, 0), (20, 0, 21, 0)
        ],
        # Keep V1 but extend close lock to 21-23:59
        "V1 + extend close 21-23:59": [
            (12, 30, 14, 0), (17, 0, 21, 0), (21, 0, 23, 59)
        ],
        # 17-22 cuts H=21 too
        "Lunch + 17-22":     [(12, 30, 14, 0), (17, 0, 22, 0)],
        # No evening BO at all
        "Lunch only":        [(12, 30, 14, 0)],
        # Pre-US no-trade zone
        "V1 + 14:30-15":     [(12, 30, 14, 0), (14, 30, 15, 0), (17, 0, 21, 0)],
        "V1 + 15-16":        [(12, 30, 14, 0), (15, 0, 16, 0), (17, 0, 21, 0)],
    }

    # 1) Test each blackout at risk=0.55% (just over $2,500 with V1 anchor)
    print("\n--- 1) NOBE @ 0.55% across blackout candidates ---")
    for lab, windows in BO.items():
        engine = build_engine(windows + [(22, 0, 23, 59)])
        bench(f"[{lab}]", **_common(0.0055, engine, MASTER_NOBE)); n += 1

    # 2) Risk sweep on the best blackouts (will identify in code)
    print("\n--- 2) Risk sweep on Lunch + 18-19, 20-21 surgical config ---")
    surgical = [(12, 30, 14, 0), (18, 0, 19, 0), (20, 0, 21, 0)]
    eng = build_engine(surgical + [(22, 0, 23, 59)])
    for r in (0.0060, 0.0058, 0.0055, 0.0052, 0.0050, 0.0045, 0.0040):
        bench(f"Surgical risk={r*100:.2f}%", **_common(r, eng, MASTER_NOBE)); n += 1

    # 3) Risk sweep on V1+lunch_widen (12:00 start)
    print("\n--- 3) Risk sweep on V1+lunch_widen ---")
    eng = build_engine([(12, 0, 14, 0), (17, 0, 21, 0), (22, 0, 23, 59)])
    for r in (0.0060, 0.0055, 0.0050, 0.0045, 0.0040):
        bench(f"V1+wide risk={r*100:.2f}%", **_common(r, eng, MASTER_NOBE)); n += 1

    # 4) Risk sweep on V1+15-16 (cut lossy mid-afternoon)
    print("\n--- 4) Risk sweep on V1+15-16 ---")
    eng = build_engine([(12, 30, 14, 0), (15, 0, 16, 0), (17, 0, 21, 0), (22, 0, 23, 59)])
    for r in (0.0060, 0.0055, 0.0050, 0.0045, 0.0040):
        bench(f"V1+15-16 risk={r*100:.2f}%", **_common(r, eng, MASTER_NOBE)); n += 1

    elapsed = time.time() - t0
    print(f"\nTotal sims: {n}  |  Elapsed: {elapsed:.1f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
