"""Phase 3 — 1-D sweep over V3-inherited hyper-params.

Baseline = V3 winner migrated to V4 (= reproduces V3 trades).

Strategy: pick a focused grid for each numeric param around the baseline value,
then a small set for booleans. We DELIBERATELY do not run a full grid here —
just 1-D scans, ~150 sims total, to feed Phase 8 combos.

Mf_length and risk_per_trade are known non-monotone on V3 (per user memory):
mf_length is included here with a fine grid; risk_per_trade lives in Phase 5.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from scripts.goals._shared.engine_settings import make_engine_settings
from scripts.goals._shared.harness import bench

from _campaign import (
    BASELINE_ACTIVE_BLACKOUTS,
    BASELINE_V4_PARAMS,
    END,
    INITIAL_EQUITY,
    INTERVAL,
    MAX_CONTRACTS,
    RISK_PER_TRADE,
    START,
    STRATEGY,
    SYMBOL,
)


# 1-D sweep specs: param_name → (values_to_try)
SWEEPS = {
    # HMA Ribbon
    "ema_len":            [7, 9, 11, 13, 15, 17, 21],
    "hma1_len":           [9, 11, 13, 15, 17, 21],
    "hma2_len":           [15, 17, 21, 25, 31, 41],
    "amp_mult":           [1.0, 1.5, 2.0, 2.5, 3.0],
    "hma_pol_bars":       [0, 1, 2, 3, 5],
    "entry_window_bars":  [1, 2, 3, 5, 7, 10],
    # SSL Channel
    "ssl_len":            [40, 60, 80, 100, 120, 160],
    "ssl_mult":           [0.1, 0.15, 0.2, 0.25, 0.3],
    # 4Kings Oscillator
    "hyper_wave_length":  [5, 6, 7, 8, 9, 11, 14],
    "signal_length":      [2, 3, 4, 5, 7],
    # Smart Money Flow (non-monotone reminder)
    "mf_length":          [15, 21, 25, 28, 31, 34, 37, 41, 51],
    "mf_smooth":          [3, 5, 7, 9, 11],
    # Risk management strategy-internal
    "tick_buffer":        [0, 1, 2, 4, 8],
    "max_sl_points":      [100.0, 200.0, 300.0, 500.0, 1000.0],
    "cooldown_bars":      [0, 1, 2, 3, 5, 8],
    "max_candle_pct":     [0.5, 0.7, 0.9, 1.0, 1.5],
    # Thresholds (only relevant when corresponding filter is ON; baseline ON for these two)
    "hw_extreme":         [10.0, 15.0, 20.0, 25.0, 30.0, 40.0],
    "sig_extreme":        [20, 30, 35, 40, 50, 60],
    # Booleans
    "one_trade_per_entry_window": [True, False],
}


def _engine():
    return make_engine_settings(
        STRATEGY,
        extra_active_windows=BASELINE_ACTIVE_BLACKOUTS,
    )


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
        engine_settings=_engine(),
    )


def main() -> int:
    print("=" * 100)
    print(f"PHASE 3 — Core strategy 1-D sweeps  |  TF={INTERVAL}  baseline = V3-migrated")
    print("=" * 100)

    base = bench("V4 baseline", strategy_params=BASELINE_V4_PARAMS, **_common())
    base_ratio = base["net_pnl"] / max(base["max_dd_$"], 1.0)
    print(f"\nBaseline P/DD ratio = {base_ratio:.1f}\n")

    best_by_param = {}
    n_sims = 0

    for param, values in SWEEPS.items():
        baseline_val = BASELINE_V4_PARAMS.get(param)
        print("-" * 100)
        print(f"SWEEP {param}  (baseline = {baseline_val})")
        results = []
        for v in values:
            params = dict(BASELINE_V4_PARAMS)
            params[param] = v
            mark = " (=base)" if v == baseline_val else ""
            label = f"  {param} = {v}{mark}"
            s = bench(label, strategy_params=params, **_common())
            results.append((v, s))
            n_sims += 1
        # Find best value among those with DD < $2000
        valid = [r for r in results if r[1]["max_dd_$"] < 2000]
        if valid:
            best = max(valid, key=lambda r: r[1]["net_pnl"] / max(r[1]["max_dd_$"], 1.0))
            v, s = best
            ratio = s["net_pnl"] / max(s["max_dd_$"], 1.0)
            change = "(=base)" if v == baseline_val else f"(was {baseline_val})"
            print(f"  → best (DD<$2k): {param}={v} {change}  PnL=${s['net_pnl']:,.0f}  "
                  f"DD=${s['max_dd_$']:,.0f}  P/DD={ratio:.1f}")
            best_by_param[param] = (v, s["net_pnl"], s["max_dd_$"], ratio)
        else:
            print(f"  → no value passes DD<$2k filter")
        print()

    # Summary
    print("=" * 100)
    print("CANDIDATES TO KEEP (Δratio vs baseline, only if PnL > baseline OR P/DD > baseline+5%):")
    print("=" * 100)
    print(f"{'Param':<24}{'Best':<12}{'PnL':>12}{'DD':>10}{'P/DD':>9}{'Δratio':>10}")
    print("-" * 100)
    for param, (v, pnl, dd, ratio) in best_by_param.items():
        d_ratio = ratio - base_ratio
        flag = "← change" if v != BASELINE_V4_PARAMS.get(param) and (
            pnl > base["net_pnl"] or d_ratio > base_ratio * 0.05
        ) else ""
        print(f"{param:<24}{str(v):<12}${pnl:>10,.0f}${dd:>8,.0f}{ratio:>9.1f}{d_ratio:>+10.1f}  {flag}")
    print(f"\nTotal sims: {n_sims}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
