"""Phase 4 — Module toggles and oscillator-filter triage.

Anchor: $61,313 / $2,143 / N=785.
Sims so far ≈ 100/500.

Lever ideas:
  - Each module on/off in isolation (osc_on, ema_on, st_on, alligator_on,
    ut_on, stc_on, hma_on)
  - Each oscillator sub-filter on/off (hw_filter_on, hw_extreme_filter_on,
    cloud_filter_on, delta_filter_on)
  - Point weights for the major buckets (pts_hw_value, pts_alligator,
    pts_ut_bot, pts_stc, pts_hma_break)
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
    print(f"PHASE 4 — Module toggles + filter triage  |  {STRATEGY}  {SYMBOL} {INTERVAL}")
    print("=" * 110)

    results = []
    t0 = time.time()

    s = bench("[anchor]", strategy_params=ANCHOR_PARAMS, **_common())
    results.append(("[anchor]", s))

    # ---- Module enable/disable ----
    print("\n--- module on/off ---")
    for module in ["osc_on", "ema_on", "st_on", "alligator_on", "ut_on", "stc_on", "hma_on"]:
        for v in [False, True]:
            mark = " (=anchor)" if v == ANCHOR_PARAMS[module] else ""
            label = f"{module}={v}{mark}"
            s = bench(label, strategy_params=_override(**{module: v}), **_common())
            results.append((label, s))

    # ---- Oscillator sub-filter toggles ----
    print("\n--- oscillator sub-filters on/off ---")
    for filt in ["hw_filter_on", "hw_extreme_filter_on", "cloud_filter_on", "delta_filter_on"]:
        for v in [False, True]:
            mark = " (=anchor)" if v == ANCHOR_PARAMS[filt] else ""
            label = f"{filt}={v}{mark}"
            s = bench(label, strategy_params=_override(**{filt: v}), **_common())
            results.append((label, s))

    # ---- Point weights ----
    print("\n--- pts weights: bumps ---")
    for pts_key in [
        "pts_hw_sens", "pts_hw_value", "pts_hw_extreme", "pts_cloud", "pts_delta",
        "pts_ema_break", "pts_ema_align", "pts_st",
        "pts_alligator", "pts_alli_offset", "pts_retest_lips",
        "pts_ut_bot", "pts_stc", "pts_hma_break",
    ]:
        for v in [0, 2]:
            label = f"{pts_key}={v}"
            s = bench(label, strategy_params=_override(**{pts_key: v}), **_common())
            results.append((label, s))

    elapsed = time.time() - t0
    print(f"\nTotal: {len(results)} sims in {elapsed:.0f}s ({elapsed/len(results):.1f}s/sim)")

    print()
    print("=" * 110)
    print("TOP 20 by PnL with DD ≤ $2,143")
    print("=" * 110)
    valid = [(l, s) for l, s in results if s["max_dd_$"] <= 2143.0]
    for l, s in sorted(valid, key=lambda x: -x[1]["net_pnl"])[:20]:
        print(f"  PnL=${s['net_pnl']:>7,.0f}  DD=${s['max_dd_$']:>5,.0f}  P/DD={s['net_pnl']/max(s['max_dd_$'],1):>5.2f}  N={s['trades']:>4}  WR={s['win_rate']:.1f}%  ← {l}")

    print()
    print("=" * 110)
    print("TOP 20 by P/DD ratio (any DD)")
    print("=" * 110)
    for l, s in sorted(results, key=lambda x: -x[1]["net_pnl"]/max(x[1]["max_dd_$"], 1.0))[:20]:
        print(f"  P/DD={s['net_pnl']/max(s['max_dd_$'],1):>5.2f}  PnL=${s['net_pnl']:>7,.0f}  DD=${s['max_dd_$']:>6,.0f}  N={s['trades']:>4}  ← {l}")

    print()
    print("=" * 110)
    print("TOP 20 by absolute PnL")
    print("=" * 110)
    for l, s in sorted(results, key=lambda x: -x[1]["net_pnl"])[:20]:
        print(f"  PnL=${s['net_pnl']:>7,.0f}  DD=${s['max_dd_$']:>6,.0f}  P/DD={s['net_pnl']/max(s['max_dd_$'],1):.2f}  N={s['trades']:>4}  ← {l}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
