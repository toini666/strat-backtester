"""Phase 1 — Selectivity (thresholds + min_gap + candle filter).

Baseline (default params): PnL=$39,124, DD=$7,884, N=2582, WR=38.8%, PF=1.11.
DD is ~3.1x our budget; need much tighter entry filtering. 1-D sweep on each
selectivity lever, mark non-monotone behaviour, then take the survivors forward.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from scripts.goals._shared.harness import bench

from _campaign import (
    BASELINE_PARAMS,
    END,
    INITIAL_EQUITY,
    INTERVAL,
    MAX_CONTRACTS,
    RISK_PER_TRADE,
    START,
    STRATEGY,
    SYMBOL,
    baseline_engine,
)


SWEEPS = {
    "long_threshold":  [4, 5, 6, 7, 8, 9, 10],
    "short_threshold": [4, 5, 6, 7, 8, 9, 10],
    "min_gap":         [4, 5, 6, 7, 8, 9, 10, 11, 12],
    "max_candle_pct":  [0.15, 0.2, 0.3, 0.4, 0.6, 0.8, 1.0],
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
        engine_settings=baseline_engine(),
    )


def _override(**kwargs):
    p = dict(BASELINE_PARAMS)
    p.update(kwargs)
    return p


def main() -> int:
    print("=" * 100)
    print(f"PHASE 1 — Selectivity sweep  |  {STRATEGY}  {SYMBOL} {INTERVAL}")
    print("=" * 100)

    t0 = time.time()
    n_sims = 0
    all_results = []

    base = bench("baseline", strategy_params=BASELINE_PARAMS, **_common())
    n_sims += 1
    all_results.append(("baseline (LT=5/ST=5/gap=4)", base))

    for param, values in SWEEPS.items():
        baseline_val = BASELINE_PARAMS.get(param)
        print()
        print("-" * 100)
        print(f"SWEEP {param}  (baseline = {baseline_val})")
        for v in values:
            params = _override(**{param: v})
            mark = " (=base)" if v == baseline_val else ""
            label = f"{param}={v}{mark}"
            s = bench(label, strategy_params=params, **_common())
            n_sims += 1
            all_results.append((label, s))

    elapsed = time.time() - t0
    print()
    print(f"Total: {n_sims} sims in {elapsed:.0f}s ({elapsed/n_sims:.1f}s/sim)")

    print()
    print("=" * 100)
    print("DD-VALID configurations (DD ≤ $2,500) sorted by PnL")
    print("=" * 100)
    dd_valid = [(l, s) for l, s in all_results if s["max_dd_$"] <= 2500]
    if not dd_valid:
        print("  (none)")
    for l, s in sorted(dd_valid, key=lambda x: -x[1]["net_pnl"])[:15]:
        print(f"  PnL=${s['net_pnl']:>7,.0f}  DD=${s['max_dd_$']:>5,.0f}  N={s['trades']:>4}  WR={s['win_rate']:.1f}%  PF={s['profit_factor']}  ← {l}")

    print()
    print("=" * 100)
    print("Best 10 by absolute PnL (any DD)")
    print("=" * 100)
    for l, s in sorted(all_results, key=lambda x: -x[1]["net_pnl"])[:10]:
        p_dd = s["net_pnl"] / max(s["max_dd_$"], 1.0)
        print(f"  PnL=${s['net_pnl']:>7,.0f}  DD=${s['max_dd_$']:>6,.0f}  P/DD={p_dd:.2f}  N={s['trades']:>4}  WR={s['win_rate']:.1f}%  ← {l}")

    print()
    print("=" * 100)
    print("Best 10 by P/DD ratio (any DD)")
    print("=" * 100)
    for l, s in sorted(all_results, key=lambda x: -x[1]["net_pnl"] / max(x[1]["max_dd_$"], 1.0))[:10]:
        p_dd = s["net_pnl"] / max(s["max_dd_$"], 1.0)
        print(f"  P/DD={p_dd:>5.2f}  PnL=${s['net_pnl']:>7,.0f}  DD=${s['max_dd_$']:>6,.0f}  N={s['trades']:>4}  ← {l}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
