"""Phase 4 — Point weights and per-indicator params.

Sweep each pts_* weight to find asymmetric levers. Then quick passes
on alligator / UT / Supertrend / STC params not covered in Phase 3.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from scripts.goals._shared.harness import run_backtest, summarize, fmt_summary
from sweeps._campaign import (
    END, INITIAL_EQUITY, INTERVAL, MAX_CONTRACTS,
    SEED_PARAMS, SEED_RISK, START, STRATEGY, SYMBOL,
    make_engine_settings,
)


def run(label, overrides):
    params = dict(SEED_PARAMS); params.update(overrides)
    result = run_backtest(
        strategy_name=STRATEGY, symbol=SYMBOL, interval=INTERVAL,
        start=START, end=END, strategy_params=params,
        initial_equity=INITIAL_EQUITY, risk_per_trade=SEED_RISK,
        max_contracts=MAX_CONTRACTS, engine_settings=make_engine_settings(),
    )
    s = summarize(result); s["label"] = label
    print(f"{label:<46s} {fmt_summary(s)}")
    return s


def main():
    print("=" * 140)
    print("Phase 4 — Point weights and indicator params")
    print("Seed: PnL $75,132 / DD $2,420 / WR 39.6%")
    print("=" * 140)

    # Per memory + v3: pts_hw_value and hw_level are DEAD. pts_ema_align=2 confirmed.
    # Sweep the remaining pts_* weights individually.
    print("\n--- 4A. Point weights ---")
    for w in [0, 1, 2]:
        run(f"pts_hw_sens={w}",      {"pts_hw_sens": w})
    for w in [0, 1, 2, 3]:
        run(f"pts_hw_extreme={w}",   {"pts_hw_extreme": w})
    for w in [0, 1, 2, 3]:
        run(f"pts_cloud={w}",        {"pts_cloud": w})
    for w in [0, 1, 2, 3]:
        run(f"pts_delta={w}",        {"pts_delta": w})
    for w in [0, 1, 2, 3]:
        run(f"pts_ema_break={w}",    {"pts_ema_break": w})
    for w in [1, 2, 3]:  # seed=2 already
        run(f"pts_ema_align={w}",    {"pts_ema_align": w})
    for w in [0, 1, 2]:
        run(f"pts_st={w}",           {"pts_st": w})
    for w in [0, 1, 2]:
        run(f"pts_alligator={w}",    {"pts_alligator": w})
    for w in [0, 1, 2]:
        run(f"pts_alli_offset={w}",  {"pts_alli_offset": w})
    for w in [0, 1, 2]:
        run(f"pts_retest_lips={w}",  {"pts_retest_lips": w})
    for w in [0, 1, 2]:
        run(f"pts_ut_bot={w}",       {"pts_ut_bot": w})
    for w in [0, 1, 2]:
        run(f"pts_stc={w}",          {"pts_stc": w})
    for w in [0, 1, 2]:
        run(f"pts_hma_break={w}",    {"pts_hma_break": w})
    for w in [0, 1, 2]:
        run(f"pts_hma_slow={w}",     {"pts_hma_slow": w})

    print("\n--- 4B. min_gap fine sweep (seed=10) ---")
    for g in [7, 8, 9, 10, 11, 12]:
        run(f"min_gap={g}", {"min_gap": g})

    print("\n--- 4C. EMA lengths (seed prin=30, sec=20) ---")
    for prin in [20, 25, 30, 35, 50]:
        run(f"ema_prin_len={prin}", {"ema_prin_len": prin})
    for sec in [9, 13, 20, 25, 30]:
        run(f"ema_sec_len={sec}", {"ema_sec_len": sec})

    print("\n--- 4D. Supertrend (seed atr=10, mult=3) ---")
    for atr in [7, 10, 14, 21]:
        run(f"st_atr={atr}", {"st_atr": atr})
    for mult in [2.0, 2.5, 3.0, 3.5, 4.0]:
        run(f"st_mult={mult}", {"st_mult": mult})

    print("\n--- 4E. UT Bot (seed key=1, atr=10) ---")
    for k in [0.5, 1.0, 1.5, 2.0]:
        run(f"ut_key={k}", {"ut_key": k})
    for a in [7, 10, 14]:
        run(f"ut_atr_period={a}", {"ut_atr_period": a})


if __name__ == "__main__":
    main()
