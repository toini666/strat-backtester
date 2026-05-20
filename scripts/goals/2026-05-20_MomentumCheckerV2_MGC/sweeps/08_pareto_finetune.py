"""Phase 8 — Pareto fine-tune.

After Phase 7, MASTER @ 0.55% / V1 blackouts:
  PnL=$56,891 / DD=$2,749 / N=807 / WR=39.4% / PF=1.54
This is $249 over the $2,500 hard ceiling.

Two paths to explore:
  1. Fine risk sweep around 0.55% to find DD under $2,500.
  2. Tighter sl_max_points + lower risk → cap individual losses → maybe
     reach the $2,000 soft target by reducing the 1-contract floor effect.
  3. Drop be_at_rr=2 (E) — it adds DD floor since BE trades close at $0
     with fees. Compare to D-only / C-only variants.
"""

from __future__ import annotations

import sys
import time
from itertools import product
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

# Variant without BE
MASTER_NOBE = dict(MASTER); MASTER_NOBE["be_at_rr"] = 0.0


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
        engine_settings=anchor_engine(),
        strategy_params=params,
    )


def main() -> int:
    print("=" * 110)
    print(f"PHASE 8 — Pareto fine-tune  |  {STRATEGY}  {SYMBOL} {INTERVAL}")
    print(f"Reference: MASTER @ 0.55% — PnL=$56,891 / DD=$2,749 (over by $249)")
    print("=" * 110)

    t0 = time.time()
    n = 0

    # 1) Fine risk sweep around 0.55% — find sub-$2,500 sweet spot
    print("\n--- 1) Fine risk sweep on MASTER ---")
    for r in (0.0058, 0.0057, 0.0056, 0.0055, 0.0054, 0.0053, 0.0052, 0.0051, 0.0050):
        bench(f"MASTER risk={r*100:.2f}%", **_common(r, MASTER)); n += 1

    # 2) Drop be_at_rr (E) — does it help DD?
    print("\n--- 2) Without BE (drop E) — same combo, fine risk ---")
    for r in (0.0060, 0.0055, 0.0050, 0.0045, 0.0040, 0.0035, 0.0030):
        bench(f"NOBE risk={r*100:.2f}%", **_common(r, MASTER_NOBE)); n += 1

    # 3) Tighter sl_max at lower risk → cap 1-contract loss size
    print("\n--- 3) Tighter sl_max + lower risk (aim sub-$2k) ---")
    for slm in (30, 40, 50, 60, 80):
        for r in (0.0050, 0.0040, 0.0030):
            p = dict(MASTER); p["sl_max_points"] = float(slm)
            bench(f"sl_max={slm} risk={r*100:.2f}%", **_common(r, p)); n += 1

    # 4) Add F (tick_buffer=3) and explore very tight sl_max
    print("\n--- 4) Aggressive DD compression (sl_max ≤ 50 + tick_buffer=3) ---")
    for slm in (25, 30, 35, 40, 50):
        p = dict(MASTER); p["sl_max_points"] = float(slm); p["tick_buffer"] = 3
        bench(f"sl_max={slm} +F risk=0.40%", **_common(0.0040, p)); n += 1
        bench(f"sl_max={slm} +F risk=0.30%", **_common(0.0030, p)); n += 1

    elapsed = time.time() - t0
    print(f"\nTotal sims: {n}  |  Elapsed: {elapsed:.1f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
