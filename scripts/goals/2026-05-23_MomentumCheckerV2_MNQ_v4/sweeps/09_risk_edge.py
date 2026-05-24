"""Phase 9 — Risk edge crawl right up to the DD=$2,420 budget.

Anchor: ema_prin=34 + ema_sec=18 + st_atr=14 + tb=0 + sl_max=42 + BO+07-08
At r=0.62%: DD $2,316 (under). At r=0.63%: DD $2,427 (just over).
Crawl 0.620 → 0.630 in steps of 0.0005 to find exact max-PnL DD-safe.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from scripts.goals._shared.harness import run_backtest, summarize, fmt_summary
from sweeps._campaign import (
    END, INITIAL_EQUITY, INTERVAL, MAX_CONTRACTS,
    SEED_PARAMS, SEED_RISK, SEED_BLACKOUTS, START, STRATEGY, SYMBOL,
    make_engine_settings,
)


BO_0708 = [
    {"active": True, "start_hour": 7, "start_minute": 0,
     "end_hour": 8, "end_minute": 0},
]


def run(label, overrides=None, risk=None, blackouts=None):
    params = dict(SEED_PARAMS)
    params.update({
        "ema_prin_len": 34, "ema_sec_len": 18, "st_atr": 14,
        "tick_buffer": 0, "sl_max_points": 42,
    })
    if overrides:
        params.update(overrides)
    bo = blackouts if blackouts is not None else SEED_BLACKOUTS + BO_0708
    r = risk if risk is not None else SEED_RISK
    result = run_backtest(
        strategy_name=STRATEGY, symbol=SYMBOL, interval=INTERVAL,
        start=START, end=END, strategy_params=params,
        initial_equity=INITIAL_EQUITY, risk_per_trade=r,
        max_contracts=MAX_CONTRACTS,
        engine_settings=make_engine_settings(blackouts=bo),
    )
    s = summarize(result); s["label"] = label
    print(f"{label:<60s} {fmt_summary(s)}")
    return s


def main():
    print("=" * 130)
    print("Phase 9 — Risk edge crawl + last blackout combos")
    print("DD budget: $2,420 (seed level)")
    print("=" * 130)

    print("\n--- 9A. Fine risk crawl ---")
    for r_pct in [0.620, 0.622, 0.624, 0.625, 0.626, 0.627, 0.628, 0.629, 0.630]:
        run(f"risk={r_pct:.3f}%", risk=r_pct / 100)

    print("\n--- 9B. BO additions to WIN-DDSAFE ---")
    BO_1430_1530 = [{"active": True, "start_hour": 14, "start_minute": 30,
                     "end_hour": 15, "end_minute": 30}]
    BO_0102 = [{"active": True, "start_hour": 1, "start_minute": 0,
                "end_hour": 2, "end_minute": 0}]
    run("anchor r=0.62 + BO+14:30-15:30",
        risk=0.0062, blackouts=SEED_BLACKOUTS + BO_0708 + BO_1430_1530)
    run("anchor r=0.62 + BO+01-02",
        risk=0.0062, blackouts=SEED_BLACKOUTS + BO_0708 + BO_0102)
    run("anchor r=0.62 + BO+01-02 + BO+14:30-15:30",
        risk=0.0062, blackouts=SEED_BLACKOUTS + BO_0708 + BO_0102 + BO_1430_1530)

    print("\n--- 9C. Higher risk under DD<=2420 with alternate combos ---")
    # Maybe a slightly different param combo allows higher risk within DD budget
    for r_pct in [0.625, 0.627, 0.630]:
        run(f"anchor r={r_pct}%", risk=r_pct / 100)
        run(f"sl_max=41 r={r_pct}%", {"sl_max_points": 41}, risk=r_pct / 100)
        run(f"sl_max=43 r={r_pct}%", {"sl_max_points": 43}, risk=r_pct / 100)

    print("\n--- 9D. Reference: SEED baseline once more ---")
    # Just to confirm no drift
    result = run_backtest(
        strategy_name=STRATEGY, symbol=SYMBOL, interval=INTERVAL,
        start=START, end=END, strategy_params=SEED_PARAMS,
        initial_equity=INITIAL_EQUITY, risk_per_trade=SEED_RISK,
        max_contracts=MAX_CONTRACTS,
        engine_settings=make_engine_settings(),
    )
    s = summarize(result); s["label"] = "SEED (control)"
    print(f"{'SEED (control)':<60s} {fmt_summary(s)}")


if __name__ == "__main__":
    main()
