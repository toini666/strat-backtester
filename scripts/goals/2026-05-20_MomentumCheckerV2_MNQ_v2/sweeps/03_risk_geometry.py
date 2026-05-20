"""Phase 3 (v2) — Risk geometry around B baseline.

sl_lookback, sl_max_points, rr_tp, tick_buffer. With patched $DD.
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
    RISK_PER_TRADE, START, STRATEGY, SYMBOL, anchor_engine,
)


SWEEPS = {
    "sl_lookback":    [3, 4, 5, 6, 7, 8, 10, 12, 15, 20],
    "sl_max_points":  [30.0, 40.0, 50.0, 60.0, 75.0, 90.0, 120.0, 200.0, 999.0],
    "rr_tp":          [1.5, 1.75, 2.0, 2.25, 2.5, 2.75, 3.0, 3.5, 4.0],
    "tick_buffer":    [0, 1, 2, 3, 5],
}


def _common():
    return dict(
        strategy_name=STRATEGY, symbol=SYMBOL, interval=INTERVAL,
        start=START, end=END,
        initial_equity=INITIAL_EQUITY, risk_per_trade=RISK_PER_TRADE,
        max_contracts=MAX_CONTRACTS, engine_settings=anchor_engine(),
    )


def _override(**kw):
    p = dict(BASELINE_PARAMS)
    p.update(kw)
    return p


def main() -> int:
    print("=" * 110)
    print(f"PHASE 3 (v2) — Risk geometry  |  B baseline")
    print("=" * 110)

    results = []
    t0 = time.time()
    s = bench("[B baseline]", strategy_params=BASELINE_PARAMS, **_common())
    results.append(("[B baseline]", s))

    for param, values in SWEEPS.items():
        base = BASELINE_PARAMS.get(param)
        print(f"\n--- {param} (B={base}) ---")
        for v in values:
            mark = " (=B)" if v == base else ""
            label = f"{param}={v}{mark}"
            s = bench(label, strategy_params=_override(**{param: v}), **_common())
            results.append((label, s))

    elapsed = time.time() - t0
    print(f"\nTotal: {len(results)} sims in {elapsed:.0f}s ({elapsed/len(results):.1f}s/sim)")

    for cap, lbl in [(3074, "V1 ceiling"), (2500, "moderate"), (2000, "target")]:
        valid = [(l, s) for l, s in results if s["max_dd_$"] <= cap]
        print()
        print("=" * 110)
        print(f"TOP 15 by PnL with $DD ≤ ${cap:,} ({lbl})")
        print("=" * 110)
        for l, s in sorted(valid, key=lambda x: -x[1]["net_pnl"])[:15]:
            print(f"  PnL=${s['net_pnl']:>7,.0f}  $DD=${s['max_dd_$']:>5,.0f}  P/DD={s['net_pnl']/max(s['max_dd_$'],1):>5.2f}  N={s['trades']:>4}  WR={s['win_rate']:.1f}%  ← {l}")

    print()
    print("=" * 110)
    print("TOP 15 by absolute PnL")
    print("=" * 110)
    for l, s in sorted(results, key=lambda x: -x[1]["net_pnl"])[:15]:
        print(f"  PnL=${s['net_pnl']:>7,.0f}  $DD=${s['max_dd_$']:>6,.0f}  P/DD={s['net_pnl']/max(s['max_dd_$'],1):.2f}  N={s['trades']:>4}  ← {l}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
