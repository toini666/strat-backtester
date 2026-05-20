"""Phase 9 — Blackout sweep on the Phase 6 winner.

From Phase 8 hour analysis the worst hours are:
  H=01 (-$1,725), H=17 (-$1,668), H=13 (-$1,252), H=20 (-$1,164),
  H=18 (-$574),   H=09 (-$415),   H=00 (-$267),   H=19 (-$184)
Total lost: ~$7,250 over these eight hours.

Goal: cut DD by removing these hours. Try multiple blackout configurations and
keep the one with highest PnL at DD ≤ $2,500.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path
from copy import deepcopy

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from backend.api import BlackoutWindowSettings

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


WINNER = dict(BASELINE_PARAMS)
WINNER.update({
    "min_gap": 9,
    "rr_tp": 2.5,
    "tick_buffer": 0,
    "hw_extreme_filter_on": True,
    "rob_on": False,
    "hw_extreme": 20.0,
    "mf_smooth": 5,
    "st_atr": 14,
    "ema_sec_len": 20,
    "amp_mult": 2.5,
})


def _engine_with_extra_blackouts(extras: list[tuple[int, int, int, int]]):
    """Return baseline engine settings + the given (sh,sm,eh,em) windows as ACTIVE."""
    e = baseline_engine()
    for (sh, sm, eh, em) in extras:
        e.blackout_windows.append(
            BlackoutWindowSettings(active=True, start_hour=sh, start_minute=sm,
                                   end_hour=eh, end_minute=em)
        )
    return e


def _common(engine):
    return dict(
        strategy_name=STRATEGY,
        symbol=SYMBOL,
        interval=INTERVAL,
        start=START,
        end=END,
        strategy_params=WINNER,
        initial_equity=INITIAL_EQUITY,
        risk_per_trade=RISK_PER_TRADE,
        max_contracts=MAX_CONTRACTS,
        engine_settings=engine,
    )


def main() -> int:
    print("=" * 100)
    print("PHASE 9 — Blackout sweep on Phase 6 winner")
    print("=" * 100)

    t0 = time.time()
    results = []
    base = bench("No extra blackout", **_common(baseline_engine()))
    results.append(("No extra blackout", base, []))

    print()
    print("-" * 100)
    print("SINGLE-HOUR BLACKOUTS (the 8 worst hours)")
    print("-" * 100)
    single_hours = [0, 1, 9, 13, 17, 18, 19, 20]
    for h in single_hours:
        windows = [(h, 0, h + 1, 0)]
        label = f"BO H={h:02d}:00-{h+1:02d}:00"
        s = bench(label, **_common(_engine_with_extra_blackouts(windows)))
        results.append((label, s, windows))

    print()
    print("-" * 100)
    print("MULTI-HOUR BLACKOUT COMBOS")
    print("-" * 100)
    combos = [
        # cluster of nearby hours
        ("BO 17-21",                   [(17, 0, 21, 0)]),
        ("BO 17-20",                   [(17, 0, 20, 0)]),
        ("BO 18-21",                   [(18, 0, 21, 0)]),
        ("BO 19-21",                   [(19, 0, 21, 0)]),
        ("BO 17-21 + 13-14",           [(17, 0, 21, 0), (13, 0, 14, 0)]),
        ("BO 17-21 + 13-14 + 1-2",     [(17, 0, 21, 0), (13, 0, 14, 0), (1, 0, 2, 0)]),
        ("BO 17-21 + 13-14 + 0-2",     [(17, 0, 21, 0), (13, 0, 14, 0), (0, 0, 2, 0)]),
        ("BO 17-21 + 13-14 + 0-2 + 9-10",  [(17, 0, 21, 0), (13, 0, 14, 0), (0, 0, 2, 0), (9, 0, 10, 0)]),
        ("BO worst-8 hours each",      [(0, 0, 2, 0), (9, 0, 10, 0), (13, 0, 14, 0), (17, 0, 21, 0)]),
        # narrower trims
        ("BO 17-18 + 20-21",           [(17, 0, 18, 0), (20, 0, 21, 0)]),
        ("BO 13-14 + 17-21",           [(13, 0, 14, 0), (17, 0, 21, 0)]),
        # Try wider US blackouts
        ("BO 15:30-22 (US session)",   [(15, 30, 22, 0)]),
        ("BO 16:30-22 (UI default)",   [(16, 30, 22, 0)]),
        ("BO 16-22 + 13-14",           [(13, 0, 14, 0), (16, 0, 22, 0)]),
        # Negative diagnostic: blackout the worst three hours only
        ("BO 1-2 + 13-14 + 17-18",     [(1, 0, 2, 0), (13, 0, 14, 0), (17, 0, 18, 0)]),
        # 2-hour wins/best preservation: keep 16-17 alive
        ("BO 17-21 + 13-14 + 0-2 (final candidate)", [(17, 0, 21, 0), (13, 0, 14, 0), (0, 0, 2, 0)]),
    ]
    for label, windows in combos:
        s = bench(label, **_common(_engine_with_extra_blackouts(windows)))
        results.append((label, s, windows))

    elapsed = time.time() - t0
    print()
    print(f"Total: {len(results)} sims in {elapsed:.0f}s")

    print()
    print("=" * 100)
    print("DD-VALID (≤$2,500) results sorted by PnL")
    print("=" * 100)
    dd_valid = [(l, s, w) for l, s, w in results if s["max_dd_$"] <= 2500]
    for l, s, _ in sorted(dd_valid, key=lambda x: -x[1]["net_pnl"])[:20]:
        ratio = s["net_pnl"] / max(s["max_dd_$"], 1.0)
        print(f"  PnL=${s['net_pnl']:>7,.0f}  DD=${s['max_dd_$']:>5,.0f}  P/DD={ratio:>5.2f}  N={s['trades']:>4}  WR={s['win_rate']:.1f}%  ← {l}")
    if not dd_valid:
        print("  (none)")

    print()
    print("=" * 100)
    print("Top 15 by absolute PnL")
    print("=" * 100)
    for l, s, _ in sorted(results, key=lambda x: -x[1]["net_pnl"])[:15]:
        ratio = s["net_pnl"] / max(s["max_dd_$"], 1.0)
        print(f"  PnL=${s['net_pnl']:>7,.0f}  DD=${s['max_dd_$']:>5,.0f}  P/DD={ratio:>4.2f}  N={s['trades']:>4}  ← {l}")

    print()
    print("=" * 100)
    print("Top 15 by P/DD ratio")
    print("=" * 100)
    for l, s, _ in sorted(results, key=lambda x: -x[1]["net_pnl"] / max(x[1]["max_dd_$"], 1.0))[:15]:
        ratio = s["net_pnl"] / max(s["max_dd_$"], 1.0)
        print(f"  P/DD={ratio:>5.2f}  PnL=${s['net_pnl']:>7,.0f}  DD=${s['max_dd_$']:>5,.0f}  N={s['trades']:>4}  ← {l}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
