"""Phase 7 — Fine-tune between the two Phase-6 winners.

A combo (best strict DD ≤ 2,143):  amp_mult=3.0, max_candle_pct=0.5,
  sig_extreme=40, hma_pol_bars=20 → $65,245 / $2,143

D combo (best sub-2k DD):  same + sl_max=60, be_at_rr=1.25
  → $60,063 / $1,657

Goal: explore the DD ∈ [1,650, 2,150] band to find the joint Pareto frontier.
Things to try:
  - be_at_rr around 1.0-1.5 in finer steps
  - sl_max_points 50, 55, 60, 65, 70, 80, 90, 100 (and infinity ≈ off)
  - sl_lookback variations (saw 5 was anchor; try 4, 6, 7, 8)
  - min_gap fine variations: 8, 9, 10
  - Risk per trade fine sweep at the winning combos
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
    ANCHOR_PARAMS,
    END,
    INITIAL_EQUITY,
    INTERVAL,
    MAX_CONTRACTS,
    RISK_PER_TRADE,
    START,
    STRATEGY,
    SYMBOL,
    anchor_engine,
)


# Phase-6 best strict-DD base
BASE_A = dict(ANCHOR_PARAMS)
BASE_A.update({
    "amp_mult": 3.0,
    "max_candle_pct": 0.5,
    "sig_extreme_filter_on": True,
    "sig_extreme": 40.0,
    "hma_pol_bars": 20,
})

# Phase-6 best sub-$2k base
BASE_D = dict(BASE_A)
BASE_D.update({
    "amp_mult": 4.0,
    "sl_max_points": 60.0,
    "be_at_rr": 1.25,
})


def _common(risk=RISK_PER_TRADE):
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
    )


def main() -> int:
    print("=" * 110)
    print(f"PHASE 7 — Fine-tune A↔D frontier  |  {STRATEGY}  {SYMBOL} {INTERVAL}")
    print("=" * 110)

    results = []
    t0 = time.time()

    # Reconfirm both anchors
    sA = bench("[A base]", strategy_params=BASE_A, **_common())
    results.append(("[A base]", sA))
    sD = bench("[D base]", strategy_params=BASE_D, **_common())
    results.append(("[D base]", sD))

    # ------------------------------------------------------------------
    # Be_at_rr fine grid × sl_max around D
    # ------------------------------------------------------------------
    print("\n--- be_at_rr × sl_max fine grid (from BASE_A) ---")
    AMP_VALS = [3.0, 4.0]
    BE_VALS = [1.0, 1.1, 1.25, 1.4, 1.5, 1.75]
    SL_VALS = [55.0, 60.0, 65.0, 70.0, 80.0, 90.0]
    for amp, be, sl in product(AMP_VALS, BE_VALS, SL_VALS):
        params = dict(BASE_A)
        params.update({"amp_mult": amp, "be_at_rr": be, "sl_max_points": sl})
        label = f"amp={amp} be={be} sl={sl}"
        s = bench(label, strategy_params=params, **_common())
        results.append((label, s))

    # ------------------------------------------------------------------
    # SL lookback variations on BASE_A
    # ------------------------------------------------------------------
    print("\n--- sl_lookback (BASE_A) ---")
    for v in [3, 4, 6, 7, 8, 10]:
        params = dict(BASE_A)
        params["sl_lookback"] = v
        label = f"A sl_lookback={v}"
        s = bench(label, strategy_params=params, **_common())
        results.append((label, s))

    # ------------------------------------------------------------------
    # min_gap fine variations
    # ------------------------------------------------------------------
    print("\n--- min_gap fine (BASE_A) ---")
    for v in [8, 9, 10, 11]:
        params = dict(BASE_A)
        params["min_gap"] = v
        label = f"A min_gap={v}"
        s = bench(label, strategy_params=params, **_common())
        results.append((label, s))

    elapsed = time.time() - t0
    print(f"\nTotal: {len(results)} sims in {elapsed:.0f}s ({elapsed/len(results):.1f}s/sim)")

    print()
    print("=" * 110)
    print("TOP 25 by PnL with DD ≤ $2,143 (strict ANCHOR budget)")
    print("=" * 110)
    valid = [(l, s) for l, s in results if s["max_dd_$"] <= 2143.0]
    for l, s in sorted(valid, key=lambda x: -x[1]["net_pnl"])[:25]:
        print(f"  PnL=${s['net_pnl']:>7,.0f}  DD=${s['max_dd_$']:>5,.0f}  P/DD={s['net_pnl']/max(s['max_dd_$'],1):>5.2f}  N={s['trades']:>4}  WR={s['win_rate']:.1f}%  PF={s['profit_factor']}  ← {l}")

    print()
    print("=" * 110)
    print("TOP 25 by PnL with DD ≤ $2,000 (TARGET)")
    print("=" * 110)
    sub2k = [(l, s) for l, s in results if s["max_dd_$"] <= 2000.0]
    for l, s in sorted(sub2k, key=lambda x: -x[1]["net_pnl"])[:25]:
        print(f"  PnL=${s['net_pnl']:>7,.0f}  DD=${s['max_dd_$']:>5,.0f}  P/DD={s['net_pnl']/max(s['max_dd_$'],1):>5.2f}  N={s['trades']:>4}  WR={s['win_rate']:.1f}%  ← {l}")

    print()
    print("=" * 110)
    print("Pareto frontier: best PnL within each DD bucket")
    print("=" * 110)
    buckets = [(1500, 1700), (1700, 1850), (1850, 2000), (2000, 2143)]
    for lo, hi in buckets:
        configs = [(l, s) for l, s in results if lo < s["max_dd_$"] <= hi]
        if configs:
            best = max(configs, key=lambda x: x[1]["net_pnl"])
            l, s = best
            print(f"  DD ∈ ({lo:>4},{hi:>4}]:  PnL=${s['net_pnl']:>7,.0f}  DD=${s['max_dd_$']:>5,.0f}  P/DD={s['net_pnl']/max(s['max_dd_$'],1):>5.2f}  ← {l}")
        else:
            print(f"  DD ∈ ({lo:>4},{hi:>4}]:  (no configs)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
