"""Phase 2 — Toggle each oscillator filter ON/OFF vs the V4 baseline (= V3 winner).

Baseline V4 params have these settings (from BASELINE_V4_PARAMS):
  hw_dir_on     = False
  hw_extreme_on = True
  sig_extreme_on= True
  hw_range_on   = False
  cloud_on      = True
  delta_on      = True
  cloud_zero_on = False
  delta_ext_on  = False

For each toggleable filter we run ONE A/B: baseline_value FLIPPED. Verdict is
KEEP / REJECT / MIXED based on Δ(net_pnl/max_dd_$).
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


FILTERS = [
    "hw_dir_on",
    "hw_extreme_on",
    "sig_extreme_on",
    "hw_range_on",
    "cloud_on",
    "delta_on",
    "cloud_zero_on",
    "delta_ext_on",
]


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
    print(f"PHASE 2 — Oscillator filter activation toggles  |  TF={INTERVAL}")
    print("=" * 100)

    base = bench("V4 baseline (V3 filters)", strategy_params=BASELINE_V4_PARAMS, **_common())
    print()

    results = []
    for flag in FILTERS:
        baseline_value = BASELINE_V4_PARAMS[flag]
        new_value = not baseline_value
        params = dict(BASELINE_V4_PARAMS)
        params[flag] = new_value
        label = f"{flag}: {baseline_value} → {new_value}"
        s = bench(label, strategy_params=params, **_common())
        results.append((flag, baseline_value, new_value, s))

    # Verdict table
    print()
    print("-" * 100)
    print(f"{'Filter':<22}{'Was':<8}{'→ Now':<8}{'PnL':>12}{'ΔPnL':>11}"
          f"{'DD':>10}{'ΔDD':>9}{'N':>7}{'P/DD':>9}{'verdict':>12}")
    print("-" * 100)
    base_ratio = base["net_pnl"] / max(base["max_dd_$"], 1.0)
    for flag, was, now, s in results:
        dpnl = s["net_pnl"] - base["net_pnl"]
        ddd = s["max_dd_$"] - base["max_dd_$"]
        ratio = s["net_pnl"] / max(s["max_dd_$"], 1.0)
        # Verdict: KEEP if P/DD improves AND PnL not crushed (-25% max)
        if ratio > base_ratio * 1.03 and s["net_pnl"] > base["net_pnl"] * 0.75:
            verdict = "✅ KEEP"
        elif ratio < base_ratio * 0.97 or s["net_pnl"] < base["net_pnl"] * 0.75:
            verdict = "❌ REJECT"
        else:
            verdict = "≈ MIXED"
        print(f"{flag:<22}{str(was):<8}{str(now):<8}"
              f"${s['net_pnl']:>10,.0f}{dpnl:>+11,.0f}"
              f"${s['max_dd_$']:>8,.0f}{ddd:>+9,.0f}{s['trades']:>7}"
              f"{ratio:>9.1f}{verdict:>12}")
    print(f"\nBaseline ratio P/DD = {base_ratio:.1f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
