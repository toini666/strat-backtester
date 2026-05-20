"""Phase 9 — Risk per trade fine-tune (max 20 contracts kept).

Phase 8 winner: BO 13-14 + 20-21 → PnL=$49,195 / DD=$2,288 / P/DD=21.50.
Already DD-valid (≤$2,500). MAX_CONTRACTS=20 enforced throughout campaign.

Per user instruction: skip daily win/loss limit sweeps. Only risk_per_trade
and minor blackout edge tuning explored here.
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


def _common(engine, risk: float = RISK_PER_TRADE):
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
    print("PHASE 9 — Risk per trade fine-tune  (MAX_CONTRACTS=20)")
    print("=" * 100)

    t0 = time.time()
    results = []

    # Best Phase 8 candidates to test (each is already DD-valid at risk=0.5%)
    blackout_candidates = [
        ("BO 13-14 + 20-21",          [(13, 0, 14, 0), (20, 0, 21, 0)]),
        ("BO 13-14 + 17-21",          [(13, 0, 14, 0), (17, 0, 21, 0)]),
        ("BO 13-14 + 18-21",          [(13, 0, 14, 0), (18, 0, 21, 0)]),
        ("BO 13-14 + 18-19 + 20-21",  [(13, 0, 14, 0), (18, 0, 19, 0), (20, 0, 21, 0)]),
        ("BO 12:30-14",               [(12, 30, 14, 0)]),
    ]

    risks = [0.003, 0.0035, 0.004, 0.0045, 0.005, 0.0055, 0.006, 0.0065, 0.007, 0.008]

    for bo_label, bo_windows in blackout_candidates:
        print()
        print("-" * 100)
        print(f"RISK SWEEP @ {bo_label}")
        print("-" * 100)
        for risk in risks:
            label = f"{bo_label} | risk={risk*100:.2f}%"
            s = bench(label, **_common(_engine(bo_windows), risk=risk))
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
    print("Top 15 by absolute PnL (any DD)")
    print("=" * 100)
    for l, s in sorted(results, key=lambda x: -x[1]["net_pnl"])[:15]:
        ratio = s["net_pnl"] / max(s["max_dd_$"], 1.0)
        print(f"  PnL=${s['net_pnl']:>7,.0f}  DD=${s['max_dd_$']:>5,.0f}  P/DD={ratio:>4.2f}  N={s['trades']:>4}  ← {l}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
