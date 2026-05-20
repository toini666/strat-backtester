"""Phase 5 — Indicator length sweeps on top of Phase 4 winner.

Phase 4 winner: min_gap=9, rr_tp=2.5, tick_buffer=0, hw_extreme_filter_on=True,
rob_on=False, hw_extreme=20.0 → PnL=$34,766, DD=$3,807, P/DD=9.13.

Sweep:
- mf_length (user memory: non-monotone on HMASSLOsciV3, sweep finely)
- hyper_wave_length, signal_length, mf_smooth
- hma_ema_len, hma1_len, hma2_len, amp_mult
- ema_prin_len, ema_sec_len
- st_atr, st_mult
- ut_key, ut_atr_period
- stc_length, stc_fast_len, stc_slow_len
- alligator (jaw/teeth/lips lengths)
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


PHASE4_WINNER = dict(BASELINE_PARAMS)
PHASE4_WINNER["min_gap"] = 9
PHASE4_WINNER["rr_tp"] = 2.5
PHASE4_WINNER["tick_buffer"] = 0
PHASE4_WINNER["hw_extreme_filter_on"] = True
PHASE4_WINNER["rob_on"] = False
PHASE4_WINNER["hw_extreme"] = 20.0


SWEEPS = {
    # Oscillator (non-monotone known; finer grid)
    "mf_length":         [15, 20, 25, 28, 30, 33, 35, 38, 41, 45, 51],
    "mf_smooth":         [3, 5, 6, 7, 9, 11],
    "hyper_wave_length": [3, 4, 5, 6, 7, 9, 11],
    "signal_length":     [2, 3, 4, 5, 7],
    # HMA Ribbon
    "hma_ema_len":  [3, 5, 7, 9, 11],
    "hma1_len":     [21, 30, 42, 55, 70],
    "hma2_len":     [63, 84, 105, 130],
    "amp_mult":     [1.0, 1.5, 2.0, 2.5, 3.0],
    # Double EMA
    "ema_prin_len": [15, 20, 25, 30, 40, 50, 75],
    "ema_sec_len":  [3, 5, 7, 9, 12, 15, 20],
    # Supertrend
    "st_atr":  [5, 7, 10, 14, 20],
    "st_mult": [1.5, 2.0, 2.5, 3.0, 4.0],
    # UT Bot
    "ut_key":        [0.5, 0.75, 1.0, 1.25, 1.5, 2.0, 3.0],
    "ut_atr_period": [5, 7, 10, 14, 20],
    # STC
    "stc_length":   [8, 10, 12, 16, 21],
    "stc_fast_len": [12, 18, 23, 26, 32, 40],
    "stc_slow_len": [30, 40, 50, 65, 80],
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


def _ovr(**kw):
    p = dict(PHASE4_WINNER)
    p.update(kw)
    return p


def main() -> int:
    print("=" * 100)
    print(f"PHASE 5 — Indicator lengths on Phase 4 winner stack")
    print("=" * 100)

    t0 = time.time()
    results = []
    base = bench("Phase-4 winner", strategy_params=PHASE4_WINNER, **_common())
    base_pdd = base["net_pnl"] / max(base["max_dd_$"], 1.0)
    print(f"Base P/DD = {base_pdd:.2f}")
    results.append(("(=base)", base))

    best_by_param: dict = {}

    for param, values in SWEEPS.items():
        baseline_val = PHASE4_WINNER.get(param)
        print()
        print("-" * 100)
        print(f"SWEEP {param}  (winner baseline = {baseline_val})")
        param_results = []
        for v in values:
            mark = " (=base)" if v == baseline_val else ""
            label = f"{param}={v}{mark}"
            s = bench(label, strategy_params=_ovr(**{param: v}), **_common())
            results.append((label, s))
            param_results.append((v, s))
        # pick best by P/DD with DD≤$5000 (we'll later cut DD with blackouts/risk)
        valid = [(v, s) for v, s in param_results if s["max_dd_$"] <= 5000]
        if valid:
            bv, bs = max(valid, key=lambda x: x[1]["net_pnl"] / max(x[1]["max_dd_$"], 1.0))
            best_by_param[param] = (bv, bs)

    elapsed = time.time() - t0
    print()
    print(f"Total: {len(results)} sims in {elapsed:.0f}s")

    print()
    print("=" * 100)
    print("Best value per param (DD≤$5k filter, sorted by P/DD)")
    print("=" * 100)
    for p, (v, s) in sorted(best_by_param.items(), key=lambda x: -x[1][1]["net_pnl"] / max(x[1][1]["max_dd_$"], 1.0)):
        change = " (=base)" if v == PHASE4_WINNER.get(p) else f" (was {PHASE4_WINNER.get(p)})"
        ratio = s["net_pnl"] / max(s["max_dd_$"], 1.0)
        print(f"  {p:<22}  best={v}{change:<14}  P/DD={ratio:>5.2f}  PnL=${s['net_pnl']:>7,.0f}  DD=${s['max_dd_$']:>5,.0f}")

    print()
    print("=" * 100)
    print("Top 15 individual sims by absolute PnL")
    print("=" * 100)
    for l, s in sorted(results, key=lambda x: -x[1]["net_pnl"])[:15]:
        ratio = s["net_pnl"] / max(s["max_dd_$"], 1.0)
        print(f"  PnL=${s['net_pnl']:>7,.0f}  DD=${s['max_dd_$']:>5,.0f}  P/DD={ratio:>4.2f}  N={s['trades']:>4}  ← {l}")

    print()
    print("=" * 100)
    print("Top 15 by P/DD")
    print("=" * 100)
    for l, s in sorted(results, key=lambda x: -x[1]["net_pnl"] / max(x[1]["max_dd_$"], 1.0))[:15]:
        ratio = s["net_pnl"] / max(s["max_dd_$"], 1.0)
        print(f"  P/DD={ratio:>5.2f}  PnL=${s['net_pnl']:>7,.0f}  DD=${s['max_dd_$']:>5,.0f}  N={s['trades']:>4}  ← {l}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
