"""Phase 5 — Indicator length sweep.

Anchor: $61,313 / $2,143 / N=785.
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


# Sweeping one-at-a-time around the anchor.
SWEEPS = {
    # Oscillator
    "hyper_wave_length": [3, 4, 5, 7, 9],
    "signal_length":     [2, 3, 4, 5, 7],
    "mf_length":         [21, 28, 35, 42, 50, 60],
    "mf_smooth":         [3, 4, 5, 7, 9],
    "hw_level":          [10.0, 12.0, 14.0, 16.0, 18.0, 22.0],
    "hw_extreme":        [10.0, 15.0, 18.0, 20.0, 25.0, 30.0, 40.0],
    # EMA
    "ema_prin_len":      [13, 21, 30, 40, 50, 80],
    "ema_sec_len":       [8, 13, 20, 30, 50],
    # Supertrend
    "st_atr":            [7, 10, 14, 21, 28],
    "st_mult":           [1.5, 2.0, 2.5, 3.0, 3.5, 4.0],
    # Alligator
    "jaw_length":        [8, 13, 21],
    "teeth_length":      [5, 8, 13],
    "lips_length":       [3, 5, 8],
    # UT Bot
    "ut_key":            [0.5, 1.0, 1.5, 2.0, 3.0],
    "ut_atr_period":     [5, 7, 10, 14, 21],
    # STC
    "stc_length":        [8, 10, 12, 16, 20],
    "stc_fast_len":      [13, 20, 26, 32, 40],
    "stc_slow_len":      [35, 50, 65, 80],
    # HMA
    "hma_ema_len":       [3, 5, 7, 10, 14],
    "hma1_len":          [21, 32, 42, 55, 70],
    "hma2_len":          [63, 84, 105, 130],
    "amp_mult":          [1.5, 2.0, 2.5, 3.0, 4.0],
}


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


def _override(**kw):
    p = dict(ANCHOR_PARAMS)
    p.update(kw)
    return p


def main() -> int:
    print("=" * 110)
    print(f"PHASE 5 — Indicator length sweep  |  {STRATEGY}  {SYMBOL} {INTERVAL}")
    print("=" * 110)

    results = []
    t0 = time.time()

    s = bench("[anchor]", strategy_params=ANCHOR_PARAMS, **_common())
    results.append(("[anchor]", s))

    for param, values in SWEEPS.items():
        base = ANCHOR_PARAMS.get(param)
        print(f"\n--- {param} (anchor={base}) ---")
        for v in values:
            mark = " (=anchor)" if v == base else ""
            label = f"{param}={v}{mark}"
            s = bench(label, strategy_params=_override(**{param: v}), **_common())
            results.append((label, s))

    elapsed = time.time() - t0
    print(f"\nTotal: {len(results)} sims in {elapsed:.0f}s ({elapsed/len(results):.1f}s/sim)")

    print()
    print("=" * 110)
    print("TOP 25 by PnL with DD ≤ $2,143")
    print("=" * 110)
    valid = [(l, s) for l, s in results if s["max_dd_$"] <= 2143.0]
    for l, s in sorted(valid, key=lambda x: -x[1]["net_pnl"])[:25]:
        print(f"  PnL=${s['net_pnl']:>7,.0f}  DD=${s['max_dd_$']:>5,.0f}  P/DD={s['net_pnl']/max(s['max_dd_$'],1):>5.2f}  N={s['trades']:>4}  WR={s['win_rate']:.1f}%  ← {l}")

    print()
    print("=" * 110)
    print("TOP 25 by P/DD ratio (any DD)")
    print("=" * 110)
    for l, s in sorted(results, key=lambda x: -x[1]["net_pnl"]/max(x[1]["max_dd_$"], 1.0))[:25]:
        print(f"  P/DD={s['net_pnl']/max(s['max_dd_$'],1):>5.2f}  PnL=${s['net_pnl']:>7,.0f}  DD=${s['max_dd_$']:>6,.0f}  N={s['trades']:>4}  ← {l}")

    print()
    print("=" * 110)
    print("TOP 25 by absolute PnL")
    print("=" * 110)
    for l, s in sorted(results, key=lambda x: -x[1]["net_pnl"])[:25]:
        print(f"  PnL=${s['net_pnl']:>7,.0f}  DD=${s['max_dd_$']:>6,.0f}  P/DD={s['net_pnl']/max(s['max_dd_$'],1):.2f}  N={s['trades']:>4}  ← {l}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
