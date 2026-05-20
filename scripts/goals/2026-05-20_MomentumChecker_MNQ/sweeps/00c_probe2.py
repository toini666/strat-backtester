"""Phase 0c — Wider probe.

Phase 0b found:
- min_gap=4 is the binding constraint; raising threshold barely reduces trades.
- Trade geometry (AW=$366 AL=$209 R:R~2) is fine; WR=35.9% is borderline (need >33% with R:R=2).

Try wider levers:
- much higher min_gap (5..10)
- higher R:R (2.5..4) — fewer hits but bigger wins
- disable noisy modules (rob, stc, alligator filters)
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

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
        engine_settings=baseline_engine(),
    )


def _override(**kwargs):
    p = dict(BASELINE_PARAMS)
    p.update(kwargs)
    return p


def main() -> int:
    print("=" * 100)
    print("PHASE 0c — Wider probe")
    print("=" * 100)
    print()

    t0 = time.time()
    sims = []
    # gap sweep at baseline thresholds
    sims.append(bench("baseline",                         strategy_params=BASELINE_PARAMS, **_common()))
    sims.append(bench("min_gap=5",                        strategy_params=_override(min_gap=5), **_common()))
    sims.append(bench("min_gap=6",                        strategy_params=_override(min_gap=6), **_common()))
    sims.append(bench("min_gap=7",                        strategy_params=_override(min_gap=7), **_common()))
    sims.append(bench("min_gap=8",                        strategy_params=_override(min_gap=8), **_common()))
    sims.append(bench("min_gap=10",                       strategy_params=_override(min_gap=10), **_common()))
    # RR sweep
    sims.append(bench("rr_tp=2.5",                        strategy_params=_override(rr_tp=2.5), **_common()))
    sims.append(bench("rr_tp=3.0",                        strategy_params=_override(rr_tp=3.0), **_common()))
    sims.append(bench("rr_tp=4.0",                        strategy_params=_override(rr_tp=4.0), **_common()))
    # disable noisy modules
    sims.append(bench("rob_off",                          strategy_params=_override(rob_on=False), **_common()))
    sims.append(bench("stc_off",                          strategy_params=_override(stc_on=False), **_common()))
    sims.append(bench("alligator_off",                    strategy_params=_override(alligator_on=False), **_common()))
    sims.append(bench("ut_off",                           strategy_params=_override(ut_on=False), **_common()))
    # combo: high gap + high RR
    sims.append(bench("gap=7 rr=3",                       strategy_params=_override(min_gap=7, rr_tp=3.0), **_common()))
    sims.append(bench("gap=8 rr=3",                       strategy_params=_override(min_gap=8, rr_tp=3.0), **_common()))
    elapsed = time.time() - t0
    print(f"\nTotal: {len(sims)} sims in {elapsed:.1f}s ({elapsed/len(sims):.1f}s/sim)")

    print()
    print("=" * 100)
    print("RESULTS SORTED BY PnL (DD-valid first)")
    print("=" * 100)
    valid = [s for s in sims if s["max_dd_$"] <= 2500]
    invalid = [s for s in sims if s["max_dd_$"] > 2500]
    for s in sorted(valid, key=lambda x: -x["net_pnl"]):
        flag = " ✅" if s["net_pnl"] > 0 else "   "
        print(f"  DD-OK{flag} {s['label']:<40s} PnL=${s['net_pnl']:>8,.0f}  DD=${s['max_dd_$']:>6,.0f}  N={s['trades']:>4}  WR={s['win_rate']:.1f}%")
    print()
    print("  -- DD over budget --")
    for s in sorted(invalid, key=lambda x: -x["net_pnl"])[:5]:
        print(f"  DD-NO    {s['label']:<40s} PnL=${s['net_pnl']:>8,.0f}  DD=${s['max_dd_$']:>6,.0f}  N={s['trades']:>4}  WR={s['win_rate']:.1f}%")
    return 0


if __name__ == "__main__":
    sys.exit(main())
