"""Phase 4 (v3) — Point weights combos (v2 only tested single bumps to 2).

Try pair bumps, disabling buckets (pts=0), and trend-vs-noise re-weighting.
When raising the weights, also test compensated thresholds since adding pts
naturally bumps the points scores.

Anchor: P1 best (sl_max=40, tb=2).
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
    RISK_PER_TRADE, START, STRATEGY, SYMBOL, seed_engine,
)

P1_ANCHOR = dict(BASELINE_PARAMS)
P1_ANCHOR.update({"sl_max_points": 40.0, "tick_buffer": 2})


def _common():
    return dict(
        strategy_name=STRATEGY, symbol=SYMBOL, interval=INTERVAL,
        start=START, end=END,
        initial_equity=INITIAL_EQUITY, risk_per_trade=RISK_PER_TRADE,
        max_contracts=MAX_CONTRACTS, engine_settings=seed_engine(),
    )


def _override(**kw):
    p = dict(P1_ANCHOR)
    p.update(kw)
    return p


def main() -> int:
    print("=" * 110)
    print("PHASE 4 (v3) — Point weights combos | anchor = P1 best")
    print("Anchor: PnL=$86,619 / $DD=$2,933")
    print("=" * 110)

    results = []
    t0 = time.time()
    s = bench("[P1 anchor]", strategy_params=P1_ANCHOR, **_common())
    results.append(("[P1 anchor]", s))

    # All pts keys (skip pts_cloud_zero which is already 0)
    pts_keys = [
        "pts_hw_sens", "pts_hw_value", "pts_hw_extreme", "pts_sig_extreme",
        "pts_cloud", "pts_delta",
        "pts_ema_break", "pts_ema_align",
        "pts_st",
        "pts_alligator", "pts_alli_offset", "pts_retest_lips",
        "pts_ut_bot", "pts_stc",
        "pts_hma_break", "pts_hma_slow",
    ]

    # --- 4.1: single bumps to 2 (re-verify with new P1 anchor, may differ vs v2)
    print("\n--- single bump to 2 ---")
    for k in pts_keys:
        label = f"{k}=2"
        s = bench(label, strategy_params=_override(**{k: 2}), **_common())
        results.append((label, s))

    # --- 4.2: single disable (pts=0)
    print("\n--- single disable (pts=0) ---")
    for k in pts_keys:
        label = f"{k}=0"
        s = bench(label, strategy_params=_override(**{k: 0}), **_common())
        results.append((label, s))

    # --- 4.3: trend stack +1 vs noise stack 0 ---
    print("\n--- trend boost combos ---")
    trend_combos = [
        {"pts_ema_break": 2, "pts_ema_align": 2, "min_gap": 10},
        {"pts_st": 2, "pts_alligator": 2, "min_gap": 10},
        {"pts_st": 2, "pts_alligator": 2, "pts_alli_offset": 2, "min_gap": 11},
        {"pts_hma_break": 2, "pts_hma_slow": 2, "min_gap": 10},
        {"pts_hma_break": 2, "pts_st": 2, "min_gap": 10},
        {"pts_hma_break": 2, "pts_ema_break": 2, "min_gap": 10},
        {"pts_st": 2, "pts_ema_break": 2, "min_gap": 10},
        {"pts_st": 2, "pts_hma_break": 2, "pts_ema_break": 2, "min_gap": 11},
        # Disable noise + boost trend
        {"pts_ut_bot": 0, "pts_st": 2, "min_gap": 10},
        {"pts_ut_bot": 0, "pts_retest_lips": 0, "pts_st": 2, "pts_hma_break": 2, "min_gap": 10},
        {"pts_alli_offset": 0, "pts_st": 2, "min_gap": 9},
    ]
    for c in trend_combos:
        label = "trend:" + " ".join(f"{k.replace('pts_','')}={v}" for k, v in c.items())
        s = bench(label, strategy_params=_override(**c), **_common())
        results.append((label, s))

    # --- 4.4: oscillator boost ---
    print("\n--- oscillator boost combos ---")
    osc_combos = [
        {"pts_hw_sens": 2, "pts_hw_value": 2, "min_gap": 10},
        {"pts_hw_extreme": 2, "pts_sig_extreme": 2, "min_gap": 10},
        {"pts_cloud": 2, "pts_delta": 2, "min_gap": 10},
        {"pts_hw_extreme": 2, "pts_cloud": 2, "min_gap": 10},
        {"pts_cloud_zero": 1, "cloud_zero_filter_on": True, "min_gap": 9},
        {"pts_cloud_zero": 2, "cloud_zero_filter_on": True, "min_gap": 10},
    ]
    for c in osc_combos:
        label = "osc:" + " ".join(f"{k}={v}" for k, v in c.items())
        s = bench(label, strategy_params=_override(**c), **_common())
        results.append((label, s))

    # --- 4.5: disable noisy modules combos ---
    print("\n--- module-off combos (lower trade count, hopefully better quality) ---")
    module_combos = [
        {"pts_ut_bot": 0, "pts_stc": 0, "min_gap": 7},
        {"pts_retest_lips": 0, "pts_alli_offset": 0, "min_gap": 7},
        {"pts_hw_sens": 0, "pts_hw_value": 0, "pts_hw_extreme": 1, "min_gap": 7},
        # All but trend
        {"pts_ut_bot": 0, "pts_stc": 0, "pts_retest_lips": 0, "pts_alli_offset": 0, "min_gap": 5},
    ]
    for c in module_combos:
        label = "mod:" + " ".join(f"{k.replace('pts_','')}={v}" for k, v in c.items())
        s = bench(label, strategy_params=_override(**c), **_common())
        results.append((label, s))

    elapsed = time.time() - t0
    print(f"\nTotal: {len(results)} sims in {elapsed:.0f}s ({elapsed/len(results):.1f}s/sim)")

    for cap, lbl in [(2933, "P1 DD"), (2500, "HARD CAP"), (2000, "stretch")]:
        valid = [(l, s) for l, s in results if s["max_dd_$"] <= cap]
        print()
        print("=" * 110)
        print(f"TOP 25 by PnL with $DD ≤ ${cap:,} ({lbl})")
        print("=" * 110)
        if not valid:
            print("  (no candidates)")
        for l, s in sorted(valid, key=lambda x: -x[1]["net_pnl"])[:25]:
            print(f"  PnL=${s['net_pnl']:>+7,.0f}  $DD=${s['max_dd_$']:>5,.0f}  "
                  f"P/DD={s['net_pnl']/max(s['max_dd_$'],1):>5.2f}  "
                  f"N={s['trades']:>4}  WR={s['win_rate']:.1f}%  ← {l}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
