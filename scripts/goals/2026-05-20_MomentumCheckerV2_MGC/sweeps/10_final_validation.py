"""Phase 10 — Final validation around the winner.

Winner candidate: MASTER (with be_at_rr=2.0) + Surgical blackout @ 0.55%
  PnL=$58,249 / $DD=$2,486 / N=851 / WR=39.7% / PF=1.54  (UNDER $2,500 ceiling)

Validates:
  1. Risk neighborhood around 0.55% (proves the sweet-spot is stable)
  2. Compare to V1 anchor at same risk (confirms surgical wins)
  3. Sub-$2k alternative (best low-DD config) is provided as a soft-target
     fallback that the user can switch to in the UI.
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


WINNER = {
    **V1_COMPAT_PARAMS,
    "pts_hma_slow":     1,
    "hma_window_bars":  5,
    "max_candle_pct":   0.3,
    "ema_sec_len":      5,
    "be_at_rr":         2.0,
    "sl_max_points":    100.0,
}

SURGICAL = [(12, 30, 14, 0), (18, 0, 19, 0), (20, 0, 21, 0), (22, 0, 23, 59)]
V1_ANCHOR = [(12, 30, 14, 0), (17, 0, 21, 0), (22, 0, 23, 59)]


def _common(risk, windows, params):
    return dict(
        strategy_name=STRATEGY,
        symbol=SYMBOL,
        interval=INTERVAL,
        start=START,
        end=END,
        initial_equity=INITIAL_EQUITY,
        risk_per_trade=risk,
        max_contracts=MAX_CONTRACTS,
        engine_settings=build_engine(windows),
        strategy_params=params,
    )


def main() -> int:
    print("=" * 110)
    print(f"PHASE 10 — Final validation  |  {STRATEGY}  {SYMBOL} {INTERVAL}")
    print(f"Winner: MASTER + Surgical blackouts @ 0.55%  →  PnL $58.2k / DD $2.49k")
    print("=" * 110)

    t0 = time.time()
    n = 0

    # 1) Risk neighborhood around 0.55%
    print("\n--- 1) Fine risk band around 0.55% on WINNER + Surgical ---")
    for r in (0.0058, 0.0057, 0.0056, 0.0055, 0.0054, 0.0053, 0.0052, 0.0050, 0.0048, 0.0045, 0.0040, 0.0035, 0.0030):
        s = bench(f"risk={r*100:.2f}%", **_common(r, SURGICAL, WINNER))
        if s["max_dd_$"] <= 2500:
            print(f"  ✓ DD=${s['max_dd_$']:,.0f} ≤ $2,500 (ceiling)")
        n += 1

    # 2) Compare to V1 anchor at the same risk levels
    print("\n--- 2) Same risk levels with V1 anchor blackouts (sanity check) ---")
    for r in (0.0055, 0.0050, 0.0030):
        bench(f"V1_anchor risk={r*100:.2f}%", **_common(r, V1_ANCHOR, WINNER)); n += 1

    # 3) Identify sub-$2k candidates (will likely be none, document)
    print("\n--- 3) Sub-$2k attempt: lowest-risk + winner ---")
    for r in (0.0025, 0.0020, 0.0015, 0.0010):
        s = bench(f"sub-$2k? risk={r*100:.2f}%", **_common(r, SURGICAL, WINNER))
        if s["max_dd_$"] <= 2000:
            print(f"  ✓ DD=${s['max_dd_$']:,.0f} ≤ $2,000 (soft target)")
        n += 1

    elapsed = time.time() - t0
    print(f"\nTotal sims: {n}  |  Elapsed: {elapsed:.1f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
