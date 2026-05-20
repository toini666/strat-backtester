"""Phase 6 — Combine Phase 5 indicator winners on top of Phase 4 stack.

Phase 5 best deltas (each tested alone vs the Phase 4 baseline):
- stc_slow_len=80      (was 50)   P/DD 16.23  PnL=$44,449 DD=$2,739
- stc_fast_len=32      (was 26)   P/DD 15.70  PnL=$44,878 DD=$2,859
- stc_length=10        (was 12)   P/DD 15.21  PnL=$42,458 DD=$2,791
- ema_prin_len=25      (was 30)   P/DD 14.90  PnL=$45,349 DD=$3,044
- mf_smooth=5          (was 6)    P/DD 14.54  PnL=$42,063 DD=$2,892
- ema_sec_len=5        (was 9)    P/DD 14.51  PnL=$44,160 DD=$3,044
- amp_mult=2.5         (was 2.0)  P/DD 14.12  PnL=$42,976 DD=$3,044
- st_atr=7             (was 10)   P/DD 14.01  PnL=$44,896 DD=$3,205

We're already at $2,739 DD with one tweak — combining might cross the $2,500 line.
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


PHASE4_WINNER = dict(BASELINE_PARAMS)
PHASE4_WINNER.update({
    "min_gap": 8,
    "sl_lookback": 15,
    "rr_tp": 3.0,
    "sl_max_points": 50.0,
    "ut_on": False,
    "sig_extreme_filter_on": True,
    "hw_extreme": 15.0,
})


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


def _ovr(**kw):
    p = dict(PHASE4_WINNER)
    p.update(kw)
    return p


def main() -> int:
    print("=" * 100)
    print("PHASE 6 — Combine indicator winners")
    print("=" * 100)

    t0 = time.time()
    results = []
    results.append(("Phase-4 winner (base)", bench("Phase-4 winner (base)", strategy_params=PHASE4_WINNER, **_common())))

    combos = [
        # STC stack (single module, all three params interact)
        ("STC: len=10",                        {"stc_length": 10}),
        ("STC: len=10 + fast=32",              {"stc_length": 10, "stc_fast_len": 32}),
        ("STC: len=10 + fast=32 + slow=80",    {"stc_length": 10, "stc_fast_len": 32, "stc_slow_len": 80}),
        ("STC: len=10 + slow=80",              {"stc_length": 10, "stc_slow_len": 80}),
        ("STC: fast=32 + slow=80",             {"stc_fast_len": 32, "stc_slow_len": 80}),
        ("STC: fast=32 + slow=65",             {"stc_fast_len": 32, "stc_slow_len": 65}),
        # EMA stack
        ("EMA: prin=25",                       {"ema_prin_len": 25}),
        ("EMA: prin=25 + sec=5",               {"ema_prin_len": 25, "ema_sec_len": 5}),
        ("EMA: prin=25 + sec=3",               {"ema_prin_len": 25, "ema_sec_len": 3}),
        # Pair STC + EMA
        ("STC-best + EMA-prin25 + sec=5",      {"stc_fast_len": 32, "stc_slow_len": 80,
                                                "ema_prin_len": 25, "ema_sec_len": 5}),
        ("STC-best + EMA-prin25",              {"stc_fast_len": 32, "stc_slow_len": 80,
                                                "ema_prin_len": 25}),
        # Add mf_smooth=5 (oscillator)
        ("STC-best + EMA-best + mf_smooth=5",
            {"stc_fast_len": 32, "stc_slow_len": 80, "ema_prin_len": 25,
             "ema_sec_len": 5, "mf_smooth": 5}),
        # Add amp_mult=2.5
        ("STC-best + EMA-best + mf_smooth=5 + amp_mult=2.5",
            {"stc_fast_len": 32, "stc_slow_len": 80, "ema_prin_len": 25,
             "ema_sec_len": 5, "mf_smooth": 5, "amp_mult": 2.5}),
        # Add st_atr=7
        ("STC-best + EMA-best + mf_smooth=5 + st_atr=7",
            {"stc_fast_len": 32, "stc_slow_len": 80, "ema_prin_len": 25,
             "ema_sec_len": 5, "mf_smooth": 5, "st_atr": 7}),
        ("STC-best + EMA-best + mf_smooth=5 + amp_mult=2.5 + st_atr=7",
            {"stc_fast_len": 32, "stc_slow_len": 80, "ema_prin_len": 25,
             "ema_sec_len": 5, "mf_smooth": 5, "amp_mult": 2.5, "st_atr": 7}),
        # Try slightly bigger DD-reducing tweaks: smaller stc_length
        ("STC: len=8 + fast=32 + slow=80",     {"stc_length": 8, "stc_fast_len": 32, "stc_slow_len": 80}),
        ("STC: len=8 + slow=80",               {"stc_length": 8, "stc_slow_len": 80}),
        # Compact best stacks
        ("BEST stack v1: stc_slow=80 + ema_prin=25 + mf_smooth=5",
            {"stc_slow_len": 80, "ema_prin_len": 25, "mf_smooth": 5}),
        ("BEST stack v2: stc_slow=80 + ema_prin=25 + ema_sec=5 + amp=2.5",
            {"stc_slow_len": 80, "ema_prin_len": 25, "ema_sec_len": 5, "amp_mult": 2.5}),
        ("BEST stack v3: stc_slow=80 + ema_sec=5 + amp=2.5",
            {"stc_slow_len": 80, "ema_sec_len": 5, "amp_mult": 2.5}),
    ]

    for label, kw in combos:
        s = bench(label, strategy_params=_ovr(**kw), **_common())
        results.append((label, s))

    elapsed = time.time() - t0
    print()
    print(f"Total: {len(results)} sims in {elapsed:.0f}s")

    print()
    print("=" * 100)
    print("DD-VALID (≤$2,500) sorted by PnL")
    print("=" * 100)
    dd_valid = [(l, s) for l, s in results if s["max_dd_$"] <= 2500]
    for l, s in sorted(dd_valid, key=lambda x: -x[1]["net_pnl"])[:15]:
        ratio = s["net_pnl"] / max(s["max_dd_$"], 1.0)
        print(f"  PnL=${s['net_pnl']:>7,.0f}  DD=${s['max_dd_$']:>5,.0f}  P/DD={ratio:>5.2f}  N={s['trades']:>4}  WR={s['win_rate']:.1f}%  ← {l}")
    if not dd_valid:
        print("  (none)")

    print()
    print("=" * 100)
    print("Top 15 by P/DD ratio (any DD)")
    print("=" * 100)
    for l, s in sorted(results, key=lambda x: -x[1]["net_pnl"] / max(x[1]["max_dd_$"], 1.0))[:15]:
        ratio = s["net_pnl"] / max(s["max_dd_$"], 1.0)
        print(f"  P/DD={ratio:>5.2f}  PnL=${s['net_pnl']:>7,.0f}  DD=${s['max_dd_$']:>5,.0f}  N={s['trades']:>4}  WR={s['win_rate']:.1f}%  ← {l}")

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
