"""Phase 10 (v2) — Final validation with the extended 13-14:30 blackout.

New winner candidate:
  Strategy: amp=3.5, pts_hma_slow=1 ssl=60 hw=5, st_atr=10, tick_buffer=2
  Engine: blackouts 09-10, 13-14:30, 17-23:59 (V1 + 30min extension on 13-14)
  Risk: 0.62%
  Expected: PnL=$76,174 / $DD=$2,846 / N=797 / P/DD=26.77

Tasks:
  - Tight risk band 0.55-0.66% on the new windows
  - Test further extensions on the 13-14:30 (14:45, 15:00)
  - Test 09-10 extensions too
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
    BASELINE_PARAMS, END, INITIAL_EQUITY, INTERVAL, MAX_CONTRACTS,
    START, STRATEGY, SYMBOL, build_engine,
)


COMBO_FULL = dict(BASELINE_PARAMS)
COMBO_FULL.update({
    "amp_mult": 3.5,
    "pts_hma_slow": 1, "ssl_len": 60, "hma_window_bars": 5,
    "st_atr": 10,
    "tick_buffer": 2,
})

WINNING_WINDOWS = [(9, 0, 10, 0), (13, 0, 14, 30), (17, 0, 23, 59)]


def _common(engine, risk):
    return dict(
        strategy_name=STRATEGY, symbol=SYMBOL, interval=INTERVAL,
        start=START, end=END,
        initial_equity=INITIAL_EQUITY, risk_per_trade=risk,
        max_contracts=MAX_CONTRACTS, engine_settings=engine,
        strategy_params=COMBO_FULL,
    )


def main() -> int:
    print("=" * 110)
    print("PHASE 10 (v2) — Final validation")
    print("=" * 110)

    results = []
    t0 = time.time()

    # Tight risk sweep on winning blackout config
    print("\n--- Risk band on winning blackouts (13-14:30) ---")
    for r in [0.0055, 0.0057, 0.0058, 0.0060, 0.0061, 0.0062, 0.0063, 0.0064, 0.0065, 0.0066]:
        label = f"risk={r*100:.2f}% w=09-10,13-14:30,17-24"
        s = bench(label, **_common(build_engine(WINNING_WINDOWS), r))
        results.append((label, s))

    # Try more extensions to 13-14:xx
    print("\n--- Further extensions on the 13-14 window ---")
    for end_min in [(14, 15), (14, 45), (15, 0)]:
        wins = [(9, 0, 10, 0), (13, 0, end_min[0], end_min[1]), (17, 0, 23, 59)]
        label = f"13-{end_min[0]:02d}:{end_min[1]:02d} risk=0.62%"
        s = bench(label, **_common(build_engine(wins), 0.0062))
        results.append((label, s))

    # Try shifting/extending 09-10 window
    print("\n--- Extensions on the 09-10 window ---")
    for w in [(8, 30, 10, 0), (9, 0, 10, 30), (8, 45, 10, 15)]:
        wins = [w, (13, 0, 14, 30), (17, 0, 23, 59)]
        label = f"09-> {w[0]:02d}:{w[1]:02d}-{w[2]:02d}:{w[3]:02d} risk=0.62%"
        s = bench(label, **_common(build_engine(wins), 0.0062))
        results.append((label, s))

    # Also test risk 0.62% but with start_minute=0 for 13 window (sanity)
    # Already done above.

    elapsed = time.time() - t0
    print(f"\nTotal: {len(results)} sims in {elapsed:.0f}s")

    print()
    print("=" * 110)
    print("TOP 20 by PnL with $DD ≤ $3,074")
    print("=" * 110)
    valid = [(l, s) for l, s in results if s["max_dd_$"] <= 3074.0]
    for l, s in sorted(valid, key=lambda x: -x[1]["net_pnl"])[:20]:
        print(f"  PnL=${s['net_pnl']:>7,.0f}  $DD=${s['max_dd_$']:>5,.0f}  P/DD={s['net_pnl']/max(s['max_dd_$'],1):>5.2f}  N={s['trades']:>4}  WR={s['win_rate']:.1f}%  PF={s['profit_factor']}  ← {l}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
