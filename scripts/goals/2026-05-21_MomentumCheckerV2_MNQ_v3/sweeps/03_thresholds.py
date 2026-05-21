"""Phase 3 (v3) — Threshold / min_gap combos (v2 only did 1-D).

Allow asymmetric long_threshold vs short_threshold. Joint sweep with min_gap.
Anchor: P1 best (sl_max=40, tb=2). Engine = seed engine.
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
    print("PHASE 3 (v3) — Threshold combos | anchor = P1 best")
    print("Anchor: PnL=$86,619 / $DD=$2,933")
    print("=" * 110)

    results = []
    t0 = time.time()
    s = bench("[P1 anchor]", strategy_params=P1_ANCHOR, **_common())
    results.append(("[P1 anchor]", s))

    # --- 3.1: (long_threshold, short_threshold) × min_gap symmetric ---
    print("\n--- symmetric thresholds × min_gap ---")
    for thr in [4, 5, 6, 7]:
        for gap in [6, 7, 8, 9, 10, 11, 12]:
            if thr == 5 and gap == 9:
                continue  # anchor
            label = f"thr=({thr},{thr})  gap={gap}"
            s = bench(label, strategy_params=_override(long_threshold=thr,
                                                       short_threshold=thr,
                                                       min_gap=gap), **_common())
            results.append((label, s))

    # --- 3.2: asymmetric long vs short ---
    print("\n--- asymmetric (long, short) at gap=9 and gap=11 ---")
    for gap in [9, 11]:
        for lt in [4, 5, 6, 7]:
            for st in [4, 5, 6, 7]:
                if lt == st:
                    continue  # already covered above
                label = f"thr=({lt},{st})  gap={gap}"
                s = bench(label, strategy_params=_override(long_threshold=lt,
                                                           short_threshold=st,
                                                           min_gap=gap), **_common())
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
                  f"N={s['trades']:>4}  WR={s['win_rate']:.1f}%  ← {l}")

    print()
    print("=" * 110)
    print("TOP 20 by P/DD ratio")
    print("=" * 110)
    valid_pos = [(l, s) for l, s in results if s["net_pnl"] > 0 and s["max_dd_$"] > 0]
    for l, s in sorted(valid_pos, key=lambda x: -x[1]["net_pnl"]/x[1]["max_dd_$"])[:20]:
        print(f"  P/DD={s['net_pnl']/s['max_dd_$']:>5.2f}  "
              f"PnL=${s['net_pnl']:>+7,.0f}  $DD=${s['max_dd_$']:>5,.0f}  "
              f"N={s['trades']:>4}  ← {l}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
