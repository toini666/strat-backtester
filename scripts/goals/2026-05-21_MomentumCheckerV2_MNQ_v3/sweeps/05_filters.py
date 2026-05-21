"""Phase 5 (v3) — Candle filter × oscillator filter joint sweeps.

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
    print("PHASE 5 (v3) — Filters & candle filter | anchor = P1 best")
    print("=" * 110)

    results = []
    t0 = time.time()
    s = bench("[P1 anchor]", strategy_params=P1_ANCHOR, **_common())
    results.append(("[P1 anchor]", s))

    # max_candle_pct × sig_extreme
    print("\n--- max_candle_pct × sig_extreme ---")
    for mcp in [0.2, 0.25, 0.3, 0.35, 0.4]:
        for se in [25.0, 30.0, 40.0, 50.0, 60.0]:
            if (mcp, se) == (0.3, 40.0):
                continue
            label = f"mcp={mcp} sig_ext={se}"
            s = bench(label, strategy_params=_override(max_candle_pct=mcp,
                                                       sig_extreme=se), **_common())
            results.append((label, s))

    # hw_level × hw_extreme
    print("\n--- hw_level × hw_extreme ---")
    for lv in [12.0, 14.0, 16.0, 18.0, 20.0]:
        for ex in [15.0, 18.0, 20.0, 22.0, 25.0]:
            if (lv, ex) == (16.0, 20.0):
                continue
            label = f"hw_lev={lv} hw_ext={ex}"
            s = bench(label, strategy_params=_override(hw_level=lv,
                                                       hw_extreme=ex), **_common())
            results.append((label, s))

    elapsed = time.time() - t0
    print(f"\nTotal: {len(results)} sims in {elapsed:.0f}s ({elapsed/len(results):.1f}s/sim)")

    for cap, lbl in [(2933, "P1 DD"), (2500, "HARD CAP"), (2000, "stretch")]:
        valid = [(l, s) for l, s in results if s["max_dd_$"] <= cap]
        print()
        print("=" * 110)
        print(f"TOP 20 by PnL with $DD ≤ ${cap:,} ({lbl})")
        print("=" * 110)
        if not valid:
            print("  (no candidates)")
        for l, s in sorted(valid, key=lambda x: -x[1]["net_pnl"])[:20]:
            print(f"  PnL=${s['net_pnl']:>+7,.0f}  $DD=${s['max_dd_$']:>5,.0f}  "
                  f"P/DD={s['net_pnl']/max(s['max_dd_$'],1):>5.2f}  "
                  f"N={s['trades']:>4}  ← {l}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
