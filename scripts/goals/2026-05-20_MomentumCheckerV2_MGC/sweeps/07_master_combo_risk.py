"""Phase 7 — Master combo + risk sweep.

After Phase 6 (combo) and Phase 9 (blackouts):
  - Best strategy combo: V1-compat + {pts_hma_slow=1, hma_window_bars=5,
                                       max_candle_pct=0.3, ema_sec_len=5,
                                       be_at_rr=2.0, sl_max_points=100}
  - Best blackouts: V1 anchor (12:30-14, 17-21, 22-23:59)
  - Best result @ 0.6% risk: PnL=$59,655 / DD=$3,168 — over $2,500

To land DD under user's hard ceiling, we MUST scale risk down. This sweep
finds the right risk for DD ≤ $2,500 and DD ≤ $2,000.

Also tests two combo variants:
  - Master (B+C+D+E+sl_max=100): max PnL focus
  - Compact (B+C+D+E+sl_max=80): tighter SL cap → smaller individual losses
  - With/without tick_buffer=3 (F)
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
    anchor_engine,
    build_engine,
)


# Combo variants
MASTER = {
    **V1_COMPAT_PARAMS,
    "pts_hma_slow":     1,
    "hma_window_bars":  5,
    "max_candle_pct":   0.3,
    "ema_sec_len":      5,
    "be_at_rr":         2.0,
    "sl_max_points":    100.0,
}

COMPACT = {
    **V1_COMPAT_PARAMS,
    "pts_hma_slow":     1,
    "hma_window_bars":  5,
    "max_candle_pct":   0.3,
    "ema_sec_len":      5,
    "be_at_rr":         2.0,
    "sl_max_points":    80.0,
}

MASTER_F = dict(MASTER); MASTER_F["tick_buffer"] = 3
COMPACT_F = dict(COMPACT); COMPACT_F["tick_buffer"] = 3


def _common(risk, engine=None):
    return dict(
        strategy_name=STRATEGY,
        symbol=SYMBOL,
        interval=INTERVAL,
        start=START,
        end=END,
        initial_equity=INITIAL_EQUITY,
        risk_per_trade=risk,
        max_contracts=MAX_CONTRACTS,
        engine_settings=engine if engine else anchor_engine(),
    )


def main() -> int:
    print("=" * 110)
    print(f"PHASE 7 — Master combo + risk sweep  |  {STRATEGY}  {SYMBOL} {INTERVAL}")
    print(f"Goal: find risk where DD ≤ $2,500 (hard) and DD ≤ $2,000 (soft)")
    print("=" * 110)

    t0 = time.time()
    n = 0

    risks = [0.0060, 0.0055, 0.0050, 0.0045, 0.0040, 0.0035, 0.0030, 0.0025]

    # 1) Master @ each risk
    print("\n--- 1) MASTER combo (sl_max=100) @ V1 blackouts ---")
    for r in risks:
        bench(f"MASTER  risk={r*100:.2f}%", strategy_params=MASTER,
              **_common(r)); n += 1

    # 2) Compact @ each risk
    print("\n--- 2) COMPACT combo (sl_max=80) @ V1 blackouts ---")
    for r in risks:
        bench(f"COMPACT risk={r*100:.2f}%", strategy_params=COMPACT,
              **_common(r)); n += 1

    # 3) With tick_buffer=3
    print("\n--- 3) MASTER + F (tick_buffer=3) ---")
    for r in risks:
        bench(f"MASTER+F risk={r*100:.2f}%", strategy_params=MASTER_F,
              **_common(r)); n += 1

    # 4) Try alternative blackout: V1_17-22 (extend evening BO by 1h)
    print("\n--- 4) MASTER @ V1_17-22 blackouts ---")
    e_17_22 = build_engine([(12, 30, 14, 0), (17, 0, 22, 0), (22, 0, 23, 59)])
    for r in risks:
        bench(f"MASTER 17-22 risk={r*100:.2f}%", strategy_params=MASTER,
              **_common(r, e_17_22)); n += 1

    # 5) Master @ V1_15:30-21 (different evening start)
    print("\n--- 5) MASTER @ V1_15:30-21 blackouts ---")
    e_15_30 = build_engine([(12, 30, 14, 0), (15, 30, 21, 0), (22, 0, 23, 59)])
    for r in risks:
        bench(f"MASTER 15:30-21 risk={r*100:.2f}%", strategy_params=MASTER,
              **_common(r, e_15_30)); n += 1

    elapsed = time.time() - t0
    print(f"\nTotal sims: {n}  |  Elapsed: {elapsed:.1f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
