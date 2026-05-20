"""Phase 8c — Try to break the $2,685 DD floor.

Best so far: NOBE + Surgical blackout @ 0.55% → PnL=$57,192 / DD=$2,685
Floor is structural — 1-contract minimum × worst losing streak.

Approaches:
  1. MASTER (with BE) + Surgical at various risks.
  2. NOBE + Surgical at very low risks (does the floor breach?).
  3. Tighter sl_max with NOBE + Surgical at low risk.
  4. Reduce trade count further via higher thresholds (didn't work in P2,
     but try with Surgical now).
  5. Cooldown bars between trades.
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


MASTER = {
    **V1_COMPAT_PARAMS,
    "pts_hma_slow":     1,
    "hma_window_bars":  5,
    "max_candle_pct":   0.3,
    "ema_sec_len":      5,
    "be_at_rr":         2.0,
    "sl_max_points":    100.0,
}
NOBE = dict(MASTER); NOBE["be_at_rr"] = 0.0

SURGICAL = [(12, 30, 14, 0), (18, 0, 19, 0), (20, 0, 21, 0), (22, 0, 23, 59)]


def _common(risk, params):
    return dict(
        strategy_name=STRATEGY,
        symbol=SYMBOL,
        interval=INTERVAL,
        start=START,
        end=END,
        initial_equity=INITIAL_EQUITY,
        risk_per_trade=risk,
        max_contracts=MAX_CONTRACTS,
        engine_settings=build_engine(SURGICAL),
        strategy_params=params,
    )


def main() -> int:
    print("=" * 110)
    print(f"PHASE 8c — Try to break the DD floor  |  {STRATEGY}  {SYMBOL} {INTERVAL}")
    print(f"Best so far: NOBE+Surgical@0.55% → $57,192 / DD $2,685")
    print(f"Surgical blackouts: 12:30-14, 18-19, 20-21, 22-23:59 + auto_close 22")
    print("=" * 110)

    t0 = time.time()
    n = 0

    # 1) MASTER + Surgical at fine risk band
    print("\n--- 1) MASTER + Surgical at fine risk band ---")
    for r in (0.0060, 0.0058, 0.0056, 0.0055, 0.0054, 0.0052, 0.0050, 0.0045, 0.0040, 0.0035, 0.0030):
        bench(f"MASTER+Surgical risk={r*100:.2f}%", **_common(r, MASTER)); n += 1

    # 2) NOBE + Surgical at fine and very low risk
    print("\n--- 2) NOBE + Surgical at very low risk ---")
    for r in (0.0035, 0.0030, 0.0025, 0.0020, 0.0015, 0.0010):
        bench(f"NOBE+Surgical risk={r*100:.2f}%", **_common(r, NOBE)); n += 1

    # 3) Tight sl_max variants at low risk
    print("\n--- 3) sl_max variants at low risk on NOBE+Surgical ---")
    for slm in (60, 80, 100, 150):
        for r in (0.0050, 0.0040, 0.0030, 0.0025):
            p = dict(NOBE); p["sl_max_points"] = float(slm)
            bench(f"sl_max={slm} risk={r*100:.2f}%", **_common(r, p)); n += 1

    # 4) Cooldown bars (cool down between trades)
    print("\n--- 4) Cooldown bars on NOBE+Surgical @ 0.55% ---")
    for cd in (1, 2, 3, 5):
        p = dict(NOBE); p["cooldown_bars"] = cd
        bench(f"cooldown={cd} risk=0.55%", **_common(0.0055, p)); n += 1

    # 5) Very high thresholds (one more try)
    print("\n--- 5) Higher thresholds (8-10) on NOBE+Surgical ---")
    for th in (8, 9, 10):
        p = dict(NOBE); p["long_threshold"] = th; p["short_threshold"] = th
        bench(f"th={th}", **_common(0.0055, p)); n += 1

    elapsed = time.time() - t0
    print(f"\nTotal sims: {n}  |  Elapsed: {elapsed:.1f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
