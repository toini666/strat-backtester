"""Phase 4 (v2) — Module toggles + filter triage + pts weights around B baseline."""

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
    print("PHASE 4 (v2) — Module toggles + filters + pts weights | B baseline")
    print("=" * 110)

    results = []
    t0 = time.time()
    s = bench("[B baseline]", strategy_params=BASELINE_PARAMS, **_common())
    results.append(("[B baseline]", s))

    # Module on/off
    print("\n--- module on/off ---")
    for m in ["osc_on", "ema_on", "st_on", "alligator_on", "ut_on", "stc_on", "hma_on"]:
        label = f"{m}=False"
        s = bench(label, strategy_params=_override(**{m: False}), **_common())
        results.append((label, s))

    # Sub-filter toggles
    print("\n--- sub-filter toggles ---")
    for f in ["hw_filter_on", "hw_extreme_filter_on", "cloud_filter_on", "delta_filter_on", "sig_extreme_filter_on"]:
        for v in [False, True]:
            if v == BASELINE_PARAMS[f]:
                continue
            label = f"{f}={v}"
            s = bench(label, strategy_params=_override(**{f: v}), **_common())
            results.append((label, s))

    # Point weights — bump up to 2
    print("\n--- pts bumps to 2 ---")
    for k in ["pts_hw_sens", "pts_hw_value", "pts_hw_extreme", "pts_sig_extreme",
              "pts_cloud", "pts_delta", "pts_ema_break", "pts_ema_align",
              "pts_st", "pts_alligator", "pts_alli_offset", "pts_retest_lips",
              "pts_ut_bot", "pts_stc", "pts_hma_break"]:
        label = f"{k}=2"
        s = bench(label, strategy_params=_override(**{k: 2}), **_common())
        results.append((label, s))

    elapsed = time.time() - t0
    print(f"\nTotal: {len(results)} sims in {elapsed:.0f}s")

    for cap, lbl in [(3074, "V1 ceiling"), (2500, "moderate"), (2000, "target")]:
        valid = [(l, s) for l, s in results if s["max_dd_$"] <= cap]
        print()
        print("=" * 110)
        print(f"TOP 15 by PnL with $DD ≤ ${cap:,} ({lbl})")
        print("=" * 110)
        for l, s in sorted(valid, key=lambda x: -x[1]["net_pnl"])[:15]:
            print(f"  PnL=${s['net_pnl']:>7,.0f}  $DD=${s['max_dd_$']:>5,.0f}  P/DD={s['net_pnl']/max(s['max_dd_$'],1):>5.2f}  N={s['trades']:>4}  ← {l}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
