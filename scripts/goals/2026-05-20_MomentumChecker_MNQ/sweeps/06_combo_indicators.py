"""Phase 6 — Combine the Phase 5 indicator winners.

Phase 5 best individuals on the Phase-4 stack:
  mf_smooth=5         → P/DD=11.99 PnL=$39,191 DD=$3,270
  st_atr=14           → P/DD=11.14 PnL=$35,854 DD=$3,218
  hma_ema_len=11      → P/DD=10.73 PnL=$32,622 DD=$3,039 (DD champion)
  stc_slow_len=65     → P/DD=10.52 PnL=$36,048 DD=$3,428
  ema_sec_len=20      → P/DD=10.29 PnL=$36,028 DD=$3,502
  ut_atr_period=14    → P/DD= 9.89 PnL=$35,074 DD=$3,546
  amp_mult=2.5        → P/DD= 9.84 PnL=$36,006 DD=$3,661
  ut_key=0.75         → P/DD= 9.51 PnL=$33,084 DD=$3,480
  ema_prin_len=40     → P/DD= 9.28 PnL=$35,391 DD=$3,814

Build progressive stacks and find the combo that maximises PnL with low DD.
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
PHASE4_WINNER["min_gap"] = 9
PHASE4_WINNER["rr_tp"] = 2.5
PHASE4_WINNER["tick_buffer"] = 0
PHASE4_WINNER["hw_extreme_filter_on"] = True
PHASE4_WINNER["rob_on"] = False
PHASE4_WINNER["hw_extreme"] = 20.0


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
    print("PHASE 6 — Combine Phase 5 winners")
    print("=" * 100)

    t0 = time.time()
    results = []
    results.append(("Phase-4 base", bench("Phase-4 base", strategy_params=PHASE4_WINNER, **_common())))

    # Progressive stack — add one at a time in order of P/DD improvement
    print()
    print("-" * 100)
    print("PROGRESSIVE STACK (add wins one by one)")
    print("-" * 100)
    progressive = [
        ("+mf_smooth=5",                                  {"mf_smooth": 5}),
        ("+st_atr=14",                                    {"mf_smooth": 5, "st_atr": 14}),
        ("+hma_ema_len=11",                               {"mf_smooth": 5, "st_atr": 14, "hma_ema_len": 11}),
        ("+stc_slow_len=65",                              {"mf_smooth": 5, "st_atr": 14, "hma_ema_len": 11, "stc_slow_len": 65}),
        ("+ema_sec_len=20",                               {"mf_smooth": 5, "st_atr": 14, "hma_ema_len": 11, "stc_slow_len": 65, "ema_sec_len": 20}),
        ("+ut_atr_period=14",                             {"mf_smooth": 5, "st_atr": 14, "hma_ema_len": 11, "stc_slow_len": 65, "ema_sec_len": 20, "ut_atr_period": 14}),
        ("+amp_mult=2.5",                                 {"mf_smooth": 5, "st_atr": 14, "hma_ema_len": 11, "stc_slow_len": 65, "ema_sec_len": 20, "ut_atr_period": 14, "amp_mult": 2.5}),
        ("+ut_key=0.75",                                  {"mf_smooth": 5, "st_atr": 14, "hma_ema_len": 11, "stc_slow_len": 65, "ema_sec_len": 20, "ut_atr_period": 14, "amp_mult": 2.5, "ut_key": 0.75}),
        ("+ema_prin_len=40",                              {"mf_smooth": 5, "st_atr": 14, "hma_ema_len": 11, "stc_slow_len": 65, "ema_sec_len": 20, "ut_atr_period": 14, "amp_mult": 2.5, "ut_key": 0.75, "ema_prin_len": 40}),
    ]
    for label, kw in progressive:
        s = bench(label, strategy_params=_ovr(**kw), **_common())
        results.append((label, s))

    # Pairwise (just a few interesting ones — too many for full pairs)
    print()
    print("-" * 100)
    print("PAIRWISE / SMALL COMBOS")
    print("-" * 100)
    pairs = [
        ("mf_s=5 + st_atr=14",                            {"mf_smooth": 5, "st_atr": 14}),
        ("mf_s=5 + hma_ema_len=11",                       {"mf_smooth": 5, "hma_ema_len": 11}),
        ("mf_s=5 + ema_sec_len=20",                       {"mf_smooth": 5, "ema_sec_len": 20}),
        ("mf_s=5 + amp_mult=2.5",                         {"mf_smooth": 5, "amp_mult": 2.5}),
        ("mf_s=5 + ut_key=0.75",                          {"mf_smooth": 5, "ut_key": 0.75}),
        ("mf_s=5 + stc_slow_len=65",                      {"mf_smooth": 5, "stc_slow_len": 65}),
        ("mf_s=5 + ut_atr=14",                            {"mf_smooth": 5, "ut_atr_period": 14}),
        ("mf_s=5 + ema_prin_len=40",                      {"mf_smooth": 5, "ema_prin_len": 40}),
        ("mf_s=5 + st_atr=14 + amp_mult=2.5",             {"mf_smooth": 5, "st_atr": 14, "amp_mult": 2.5}),
        ("mf_s=5 + st_atr=14 + ema_sec_len=20",           {"mf_smooth": 5, "st_atr": 14, "ema_sec_len": 20}),
        ("mf_s=5 + st_atr=14 + stc_slow_len=65",          {"mf_smooth": 5, "st_atr": 14, "stc_slow_len": 65}),
        ("mf_s=5 + st_atr=14 + amp_mult=2.5 + stc_slow=65",      {"mf_smooth": 5, "st_atr": 14, "amp_mult": 2.5, "stc_slow_len": 65}),
        ("mf_s=5 + st_atr=14 + ema_sec=20 + amp_mult=2.5",       {"mf_smooth": 5, "st_atr": 14, "ema_sec_len": 20, "amp_mult": 2.5}),
        ("mf_s=5 + st_atr=14 + ema_sec=20 + stc_slow=65",        {"mf_smooth": 5, "st_atr": 14, "ema_sec_len": 20, "stc_slow_len": 65}),
        ("mf_s=5 + st_atr=14 + ema_sec=20 + amp_mult=2.5 + ut_atr=14", {"mf_smooth": 5, "st_atr": 14, "ema_sec_len": 20, "amp_mult": 2.5, "ut_atr_period": 14}),
    ]
    for label, kw in pairs:
        s = bench(label, strategy_params=_ovr(**kw), **_common())
        results.append((label, s))

    elapsed = time.time() - t0
    print()
    print(f"Total: {len(results)} sims in {elapsed:.0f}s")

    print()
    print("=" * 100)
    print("Top 15 by P/DD")
    print("=" * 100)
    for l, s in sorted(results, key=lambda x: -x[1]["net_pnl"] / max(x[1]["max_dd_$"], 1.0))[:15]:
        ratio = s["net_pnl"] / max(s["max_dd_$"], 1.0)
        print(f"  P/DD={ratio:>5.2f}  PnL=${s['net_pnl']:>7,.0f}  DD=${s['max_dd_$']:>5,.0f}  N={s['trades']:>4}  WR={s['win_rate']:.1f}%  ← {l}")

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
