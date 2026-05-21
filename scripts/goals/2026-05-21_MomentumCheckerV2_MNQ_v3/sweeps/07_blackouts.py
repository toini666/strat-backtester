"""Phase 7 (v3) — Blackout fine-tune on P1 anchor.

Phase 0 diagnostic showed:
  H=01: 39 trades, -$3,402 net, 21% WR → strong blackout candidate
  H=14: 60 trades, +$7 avg, 30% WR (only 14:30+ — half-blocked already)
  H=07: 47 trades, +$18 avg, 32% WR — marginal
  H=10: 58 trades, +$87 avg, 38% WR — fine

Seed blackouts (active): 9-10, 13-14:30, 17-24, 22-24

Test:
  - add 1-2 blackout for Asia-loss period
  - extend the lunch blackout
  - extend the morning blackout
  - drop the morning blackout (cheap test)
  - try 7-8 instead of 9-10
  - try 23-1 or 0-2 specifically for the losing Asia hour
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
    RISK_PER_TRADE, START, STRATEGY, SYMBOL, build_engine, seed_engine,
)

P1_ANCHOR = dict(BASELINE_PARAMS)
P1_ANCHOR.update({"sl_max_points": 40.0, "tick_buffer": 2})


def _common(engine):
    return dict(
        strategy_name=STRATEGY, symbol=SYMBOL, interval=INTERVAL,
        start=START, end=END,
        initial_equity=INITIAL_EQUITY, risk_per_trade=RISK_PER_TRADE,
        max_contracts=MAX_CONTRACTS, engine_settings=engine,
    )


# Reference: seed has 9-10, 13-14:30, 17-24 (22-24 is redundant overlap)
# Each "windows" is a list of (sh, sm, eh, em) tuples for active blackouts
SCENARIOS = {
    "[seed]": [(9, 0, 10, 0), (13, 0, 14, 30), (17, 0, 23, 59)],

    # +1 Asia loss block
    "add 01-02": [(1, 0, 2, 0), (9, 0, 10, 0), (13, 0, 14, 30), (17, 0, 23, 59)],
    "add 00-02": [(0, 0, 2, 0), (9, 0, 10, 0), (13, 0, 14, 30), (17, 0, 23, 59)],
    "add 01-03": [(1, 0, 3, 0), (9, 0, 10, 0), (13, 0, 14, 30), (17, 0, 23, 59)],
    "add 23-02": [(23, 0, 23, 59), (0, 0, 2, 0), (9, 0, 10, 0), (13, 0, 14, 30), (17, 0, 23, 59)],

    # Extend lunch
    "lunch 12-14:30": [(9, 0, 10, 0), (12, 0, 14, 30), (17, 0, 23, 59)],
    "lunch 13-15:00": [(9, 0, 10, 0), (13, 0, 15, 0), (17, 0, 23, 59)],
    "lunch 12:30-14:30": [(9, 0, 10, 0), (12, 30, 14, 30), (17, 0, 23, 59)],
    "lunch 13-14:45": [(9, 0, 10, 0), (13, 0, 14, 45), (17, 0, 23, 59)],

    # Morning variants
    "morn 7-8": [(7, 0, 8, 0), (13, 0, 14, 30), (17, 0, 23, 59)],
    "morn 8-10": [(8, 0, 10, 0), (13, 0, 14, 30), (17, 0, 23, 59)],
    "morn 7-10": [(7, 0, 10, 0), (13, 0, 14, 30), (17, 0, 23, 59)],
    "no morn": [(13, 0, 14, 30), (17, 0, 23, 59)],

    # Compound H=01 + lunch ext
    "+01-02 +12:30-14:30": [(1, 0, 2, 0), (9, 0, 10, 0), (12, 30, 14, 30), (17, 0, 23, 59)],
    "+01-02 +12-14:30":    [(1, 0, 2, 0), (9, 0, 10, 0), (12, 0, 14, 30), (17, 0, 23, 59)],
    "+00-02 +12-14:30":    [(0, 0, 2, 0), (9, 0, 10, 0), (12, 0, 14, 30), (17, 0, 23, 59)],
    "+01-02 +7-10":        [(1, 0, 2, 0), (7, 0, 10, 0), (13, 0, 14, 30), (17, 0, 23, 59)],
    "+00-02 +13-15":       [(0, 0, 2, 0), (9, 0, 10, 0), (13, 0, 15, 0), (17, 0, 23, 59)],
    "+01-02 no morn":      [(1, 0, 2, 0), (13, 0, 14, 30), (17, 0, 23, 59)],
    "+01-02 morn 7-10":    [(1, 0, 2, 0), (7, 0, 10, 0), (13, 0, 14, 30), (17, 0, 23, 59)],

    # Late session
    "late 16-23:59":  [(9, 0, 10, 0), (13, 0, 14, 30), (16, 0, 23, 59)],
    "+01-02 16-23:59": [(1, 0, 2, 0), (9, 0, 10, 0), (13, 0, 14, 30), (16, 0, 23, 59)],
    "late 16:30-23:59": [(9, 0, 10, 0), (13, 0, 14, 30), (16, 30, 23, 59)],

    # Minimal Asia block
    "01-02 only-extra": [(1, 0, 2, 0), (9, 0, 10, 0), (13, 0, 14, 30), (17, 0, 23, 59)],
    "0:30-2 win": [(0, 30, 2, 0), (9, 0, 10, 0), (13, 0, 14, 30), (17, 0, 23, 59)],
    "0-1:30 win": [(0, 0, 1, 30), (9, 0, 10, 0), (13, 0, 14, 30), (17, 0, 23, 59)],
}


def main() -> int:
    print("=" * 110)
    print("PHASE 7 (v3) — Blackouts | anchor = P1 best (sl_max=40, tb=2)")
    print("Targets: H=01 (39 tr, -$3,402, 21% WR); H=07 marginal; H=14 marginal")
    print("=" * 110)

    results = []
    t0 = time.time()
    for label, windows in SCENARIOS.items():
        engine = build_engine(windows)
        s = bench(label, strategy_params=P1_ANCHOR, **_common(engine))
        results.append((label, s))

    elapsed = time.time() - t0
    print(f"\nTotal: {len(results)} sims in {elapsed:.0f}s ({elapsed/len(results):.1f}s/sim)")

    for cap, lbl in [(2933, "P1 DD"), (2500, "HARD CAP"), (2000, "stretch")]:
        valid = [(l, s) for l, s in results if s["max_dd_$"] <= cap]
        print()
        print("=" * 110)
        print(f"TOP 15 by PnL with $DD ≤ ${cap:,} ({lbl})")
        print("=" * 110)
        if not valid:
            print("  (no candidates)")
        for l, s in sorted(valid, key=lambda x: -x[1]["net_pnl"])[:15]:
            print(f"  PnL=${s['net_pnl']:>+7,.0f}  $DD=${s['max_dd_$']:>5,.0f}  "
                  f"P/DD={s['net_pnl']/max(s['max_dd_$'],1):>5.2f}  "
                  f"N={s['trades']:>4}  WR={s['win_rate']:.1f}%  ← {l}")

    print()
    print("=" * 110)
    print("TOP 15 by P/DD ratio")
    print("=" * 110)
    valid_pos = [(l, s) for l, s in results if s["net_pnl"] > 0 and s["max_dd_$"] > 0]
    for l, s in sorted(valid_pos, key=lambda x: -x[1]["net_pnl"]/x[1]["max_dd_$"])[:15]:
        print(f"  P/DD={s['net_pnl']/s['max_dd_$']:>5.2f}  "
              f"PnL=${s['net_pnl']:>+7,.0f}  $DD=${s['max_dd_$']:>5,.0f}  "
              f"N={s['trades']:>4}  ← {l}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
