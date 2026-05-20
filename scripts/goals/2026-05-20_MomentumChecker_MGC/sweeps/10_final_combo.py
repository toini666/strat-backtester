"""Phase 10 — Final refinement around the Phase 9 winner.

Phase 9 best: BO 12:30-14 + risk=0.60% → PnL=$55,270 / DD=$2,425 / P/DD=22.79.

Fine-grain explorations:
- Risk between 0.55% and 0.625% in 0.0125% steps
- Blackout edge tweaks (12:45, 12:30-13:45, 12:30-14:15)
- Pair BO 12:30-14 with extra cuts (20-21 / 17-21) to dampen DD and lift risk
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


def _engine(extras: list[tuple[int, int, int, int]]):
    e = baseline_engine()
    for (sh, sm, eh, em) in extras:
        e.blackout_windows.append(
            BlackoutWindowSettings(active=True, start_hour=sh, start_minute=sm,
                                   end_hour=eh, end_minute=em)
        )
    return e


def _common(engine, risk: float):
    return dict(
        strategy_name=STRATEGY,
        symbol=SYMBOL,
        interval=INTERVAL,
        start=START,
        end=END,
        strategy_params=WINNER,
        initial_equity=INITIAL_EQUITY,
        risk_per_trade=risk,
        max_contracts=MAX_CONTRACTS,
        engine_settings=engine,
    )


def main() -> int:
    print("=" * 100)
    print("PHASE 10 — Final refinement")
    print("=" * 100)

    t0 = time.time()
    results = []

    print()
    print("-" * 100)
    print("FINE RISK SWEEP @ BO 12:30-14")
    print("-" * 100)
    bo = [(12, 30, 14, 0)]
    for risk in [0.0550, 0.0575, 0.0600, 0.0625, 0.0650]:
        label = f"BO 12:30-14 | risk={risk*100:.2f}%"
        s = bench(label, **_common(_engine(bo), risk=risk))
        results.append((label, s))

    print()
    print("-" * 100)
    print("BLACKOUT EDGE TWEAKS @ risk=0.60%")
    print("-" * 100)
    edge_variants = [
        ("BO 12:30-14",         [(12, 30, 14, 0)]),
        ("BO 12:45-14",         [(12, 45, 14, 0)]),
        ("BO 12:30-13:45",      [(12, 30, 13, 45)]),
        ("BO 12:30-14:15",      [(12, 30, 14, 15)]),
        ("BO 12:00-14",         [(12, 0, 14, 0)]),
        ("BO 13-14",            [(13, 0, 14, 0)]),
        ("BO 12:30-14:00 + 20-21",  [(12, 30, 14, 0), (20, 0, 21, 0)]),
        ("BO 12:30-14:00 + 17-21",  [(12, 30, 14, 0), (17, 0, 21, 0)]),
        ("BO 12:30-14:00 + 18-21",  [(12, 30, 14, 0), (18, 0, 21, 0)]),
    ]
    for label, windows in edge_variants:
        s = bench(label + " | risk=0.60%", **_common(_engine(windows), risk=0.006))
        results.append((label + " | risk=0.60%", s))

    print()
    print("-" * 100)
    print("EXTENDED RISK on BO 12:30-14 + 20-21 (dampened DD)")
    print("-" * 100)
    bo = [(12, 30, 14, 0), (20, 0, 21, 0)]
    for risk in [0.0050, 0.0055, 0.0060, 0.0065, 0.0070]:
        label = f"BO 12:30-14 + 20-21 | risk={risk*100:.2f}%"
        s = bench(label, **_common(_engine(bo), risk=risk))
        results.append((label, s))

    print()
    print("-" * 100)
    print("EXTENDED RISK on BO 12:30-14 + 17-21 (dampened DD)")
    print("-" * 100)
    bo = [(12, 30, 14, 0), (17, 0, 21, 0)]
    for risk in [0.0050, 0.0055, 0.0060, 0.0065, 0.0070]:
        label = f"BO 12:30-14 + 17-21 | risk={risk*100:.2f}%"
        s = bench(label, **_common(_engine(bo), risk=risk))
        results.append((label, s))

    elapsed = time.time() - t0
    print()
    print(f"Total: {len(results)} sims in {elapsed:.0f}s")

    print()
    print("=" * 100)
    print("DD-VALID (≤$2,500) sorted by PnL")
    print("=" * 100)
    dd_valid = [(l, s) for l, s in results if s["max_dd_$"] <= 2500]
    for l, s in sorted(dd_valid, key=lambda x: -x[1]["net_pnl"])[:25]:
        ratio = s["net_pnl"] / max(s["max_dd_$"], 1.0)
        print(f"  PnL=${s['net_pnl']:>7,.0f}  DD=${s['max_dd_$']:>5,.0f}  P/DD={ratio:>5.2f}  N={s['trades']:>4}  WR={s['win_rate']:.1f}%  ← {l}")
    if not dd_valid:
        print("  (none)")

    print()
    print("=" * 100)
    print("Top 15 by absolute PnL")
    print("=" * 100)
    for l, s in sorted(results, key=lambda x: -x[1]["net_pnl"])[:15]:
        ratio = s["net_pnl"] / max(s["max_dd_$"], 1.0)
        print(f"  PnL=${s['net_pnl']:>7,.0f}  DD=${s['max_dd_$']:>5,.0f}  P/DD={ratio:>4.2f}  N={s['trades']:>4}  ← {l}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
