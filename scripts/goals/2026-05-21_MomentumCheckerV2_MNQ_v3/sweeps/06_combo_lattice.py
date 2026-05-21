"""Phase 6 (v3) — Combo lattice of best findings.

Anchor: P1 best (sl_max=40, tb=2).
Promising deltas from P4/P5:
  - (pts_ema_break=2, pts_ema_align=2, gap=10) → PnL $88,691 / DD $4,149
  - pts_sig_extreme=2 → PnL $83,868 / DD $2,933
  - mcp=0.4 sig_ext=40 → PnL $86,909 / DD $2,993
  - pts_hw_value is dead → ignore

Phase 7 (blackouts) runs separately; we combine winners later.
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
    print("PHASE 6 (v3) — Combo lattice | anchor = P1 best")
    print("=" * 110)

    results = []
    t0 = time.time()
    s = bench("[P1 anchor]", strategy_params=P1_ANCHOR, **_common())
    results.append(("[P1 anchor]", s))

    # 6.1: EMA pts × min_gap fine sweep (likely the hottest lever)
    print("\n--- pts_ema_break × pts_ema_align × min_gap ---")
    for eb in [1, 2]:
        for ea in [1, 2]:
            for gap in [9, 10, 11, 12, 13]:
                if (eb, ea, gap) == (1, 1, 9):
                    continue
                label = f"eb={eb} ea={ea} gap={gap}"
                s = bench(label, strategy_params=_override(
                    pts_ema_break=eb, pts_ema_align=ea, min_gap=gap), **_common())
                results.append((label, s))

    # 6.2: pts_sig_extreme × min_gap × sig_extreme
    print("\n--- pts_sig_extreme=2 with thresholds ---")
    for se_v in [30.0, 40.0, 50.0]:
        for gap in [9, 10]:
            label = f"pts_se=2 sig_ext={se_v} gap={gap}"
            s = bench(label, strategy_params=_override(
                pts_sig_extreme=2, sig_extreme=se_v, min_gap=gap), **_common())
            results.append((label, s))

    # 6.3: sl_max fine sweep near 40
    print("\n--- sl_max fine × tb ---")
    for sl_max in [30.0, 35.0, 40.0, 45.0]:
        for tb in [1, 2, 3]:
            if (sl_max, tb) == (40.0, 2):
                continue
            label = f"sl_max={sl_max} tb={tb}"
            s = bench(label, strategy_params=_override(
                sl_max_points=sl_max, tick_buffer=tb), **_common())
            results.append((label, s))

    # 6.4: mcp × sl_max joint
    print("\n--- mcp × sl_max ---")
    for mcp in [0.25, 0.3, 0.35]:
        for sl_max in [35.0, 40.0, 45.0]:
            if (mcp, sl_max) == (0.3, 40.0):
                continue
            label = f"mcp={mcp} sl_max={sl_max}"
            s = bench(label, strategy_params=_override(
                max_candle_pct=mcp, sl_max_points=sl_max), **_common())
            results.append((label, s))

    # 6.5: stacked best deltas
    print("\n--- stacked combos ---")
    stacks = [
        # EMA pts uplift with various controls
        {"pts_ema_break": 2, "pts_ema_align": 2, "min_gap": 11, "sl_max_points": 35.0},
        {"pts_ema_break": 2, "pts_ema_align": 2, "min_gap": 11, "sl_lookback": 7},
        {"pts_ema_break": 2, "pts_ema_align": 2, "min_gap": 12, "sl_max_points": 50.0},
        # sig_extreme stack
        {"pts_sig_extreme": 2, "sig_extreme": 30.0, "min_gap": 10},
        {"pts_sig_extreme": 2, "sig_extreme": 50.0, "min_gap": 10},
        # mcp tightening with sl_max=40
        {"max_candle_pct": 0.25, "sig_extreme": 30.0},
        {"max_candle_pct": 0.25, "sig_extreme": 50.0},
        # New stack: try sl_lookback=7 (P1 found it dropped DD to $2,930 standalone)
        {"sl_lookback": 7, "sl_max_points": 40.0, "tick_buffer": 2},
        {"sl_lookback": 7, "sl_max_points": 35.0, "tick_buffer": 2},
        {"sl_lookback": 7, "sl_max_points": 45.0, "tick_buffer": 2},
        # be_at_rr with low rr (P1 showed at rr=2 and rr=2.5 BE was bad — try high BE)
        {"be_at_rr": 1.5, "rr_tp": 2.0, "sl_max_points": 40.0},  # was -$24k vs anchor at sl_max=60
        {"be_at_rr": 1.5, "rr_tp": 2.5, "sl_max_points": 35.0},
        # Disable dead bucket
        {"pts_hw_value": 0, "min_gap": 8},
        {"pts_hw_value": 0, "min_gap": 9},
    ]
    for st in stacks:
        label = "stack:" + " ".join(f"{k}={v}" for k, v in st.items())
        s = bench(label, strategy_params=_override(**st), **_common())
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

    print()
    print("=" * 110)
    print("TOP 25 by P/DD ratio")
    print("=" * 110)
    valid_pos = [(l, s) for l, s in results if s["net_pnl"] > 0 and s["max_dd_$"] > 0]
    for l, s in sorted(valid_pos, key=lambda x: -x[1]["net_pnl"]/x[1]["max_dd_$"])[:25]:
        print(f"  P/DD={s['net_pnl']/s['max_dd_$']:>5.2f}  "
              f"PnL=${s['net_pnl']:>+7,.0f}  $DD=${s['max_dd_$']:>5,.0f}  "
              f"N={s['trades']:>4}  ← {l}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
