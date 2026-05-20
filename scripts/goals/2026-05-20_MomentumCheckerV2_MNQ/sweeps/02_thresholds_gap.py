"""Phase 2 — Thresholds & gap (selectivity).

Anchor: PnL=$61,313 / DD=$2,143 / N=785.
Phase 1 winner: sig_extreme=40 → $62,679 / DD=$2,143 / N=760.

Levers swept here:
  - long_threshold / short_threshold
  - min_gap
  - max_candle_pct
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


SWEEPS = {
    "long_threshold":   [4, 5, 6, 7, 8],
    "short_threshold":  [4, 5, 6, 7, 8],
    "min_gap":          [5, 6, 7, 8, 9, 10, 11, 12, 13],
    "max_candle_pct":   [0.2, 0.3, 0.4, 0.5, 0.6, 0.8, 1.0],
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
    print(f"PHASE 2 — Thresholds & gap sweep  |  {STRATEGY}  {SYMBOL} {INTERVAL}")
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
    print("TOP 15 by PnL with DD ≤ $2,143")
    print("=" * 110)
    valid = [(l, s) for l, s in results if s["max_dd_$"] <= 2143.0]
    for l, s in sorted(valid, key=lambda x: -x[1]["net_pnl"])[:15]:
        print(f"  PnL=${s['net_pnl']:>7,.0f}  DD=${s['max_dd_$']:>5,.0f}  P/DD={s['net_pnl']/max(s['max_dd_$'],1):>5.2f}  N={s['trades']:>4}  WR={s['win_rate']:.1f}%  PF={s['profit_factor']}  ← {l}")

    print()
    print("=" * 110)
    print("TOP 15 by P/DD ratio (any DD)")
    print("=" * 110)
    for l, s in sorted(results, key=lambda x: -x[1]["net_pnl"]/max(x[1]["max_dd_$"], 1.0))[:15]:
        print(f"  P/DD={s['net_pnl']/max(s['max_dd_$'],1):>5.2f}  PnL=${s['net_pnl']:>7,.0f}  DD=${s['max_dd_$']:>6,.0f}  N={s['trades']:>4}  ← {l}")

    print()
    print("=" * 110)
    print("TOP 15 by absolute PnL")
    print("=" * 110)
    for l, s in sorted(results, key=lambda x: -x[1]["net_pnl"])[:15]:
        print(f"  PnL=${s['net_pnl']:>7,.0f}  DD=${s['max_dd_$']:>6,.0f}  P/DD={s['net_pnl']/max(s['max_dd_$'],1):.2f}  N={s['trades']:>4}  ← {l}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
