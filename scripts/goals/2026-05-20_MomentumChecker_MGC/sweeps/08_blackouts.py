"""Phase 8 — Blackout sweep on Phase 6 winner.

Phase 6 winner = PnL $46,100 / DD $2,712. Need $212 DD cut.

From Phase 7 hour analysis (entry hours, by total PnL):
- H=23: -$2,188 (13 trades, WR 8%)        ← weird, see below
- H=13: -$1,192 (26 trades, WR 31%)       ← lunch hour
- H=18: -$  631 (30 trades, WR 50%)
- H=20: -$  311 (17 trades, WR 53%)
- H=17:  +$   66 (30 trades, ~breakeven)
Total losing PnL across H=13/18/20/23 ≈ -$4,322.

H=23 trades exist despite the 22-23:59 blackout because during DST-off periods
(winter) the entry timestamp can land in wall-clock 23:xx but reference-time
21:xx — the blackout uses reference time so it's permissive on the wall clock.
Adding a wall-clock filter would over-block during summer; better to leave that
edge case and focus on the lunch hour.

Best DoW: Mon, Tue, Fri (>$10k each). Wed weakest (+$570). Won't block by DoW.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

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
    "min_gap": 8,
    "sl_lookback": 15,
    "rr_tp": 3.0,
    "sl_max_points": 50.0,
    "ut_on": False,
    "sig_extreme_filter_on": True,
    "hw_extreme": 15.0,
    "stc_length": 10,
    "stc_fast_len": 32,
})


def _engine_with_extra_blackouts(extras: list[tuple[int, int, int, int]]):
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
    print("PHASE 8 — Blackout sweep on Phase 6 winner")
    print("=" * 100)

    t0 = time.time()
    results = []
    base = bench("No extra blackout", **_common(baseline_engine()))
    results.append(("No extra blackout", base, []))

    print()
    print("-" * 100)
    print("SINGLE-HOUR BLACKOUTS (worst losing hours)")
    print("-" * 100)
    single_hours = [13, 18, 20]
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
        # Smallest cut first
        ("BO 13-14",                                [(13, 0, 14, 0)]),
        ("BO 18-19",                                [(18, 0, 19, 0)]),
        ("BO 13-14 + 18-19",                        [(13, 0, 14, 0), (18, 0, 19, 0)]),
        ("BO 13-14 + 18-21",                        [(13, 0, 14, 0), (18, 0, 21, 0)]),
        ("BO 13-14 + 17-21",                        [(13, 0, 14, 0), (17, 0, 21, 0)]),
        ("BO 13-14 + 20-21",                        [(13, 0, 14, 0), (20, 0, 21, 0)]),
        ("BO 13-14 + 18-19 + 20-21",                [(13, 0, 14, 0), (18, 0, 19, 0), (20, 0, 21, 0)]),
        # Lunch only — see if alone is enough
        ("BO 12:30-14",                             [(12, 30, 14, 0)]),
        ("BO 12:30-13:30",                          [(12, 30, 13, 30)]),
        ("BO 13:30-14:00",                          [(13, 30, 14, 0)]),
        ("BO 12-14",                                [(12, 0, 14, 0)]),
        # Trim afternoon
        ("BO 18-21",                                [(18, 0, 21, 0)]),
        # UI default base (12-14 + 16:30-22 + 22-23:59) as a sanity check
        ("BO 12-14 + 16:30-22 (UI default)",        [(12, 0, 14, 0), (16, 30, 22, 0)]),
    ]
    for label, windows in combos:
        s = bench(label, **_common(_engine_with_extra_blackouts(windows)))
        results.append((label, s, windows))

    elapsed = time.time() - t0
    print()
    print(f"Total: {len(results)} sims in {elapsed:.0f}s")

    print()
    print("=" * 100)
    print("DD-VALID (≤$2,500) sorted by PnL")
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
