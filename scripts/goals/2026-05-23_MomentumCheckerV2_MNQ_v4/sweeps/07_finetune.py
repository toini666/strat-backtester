"""Phase 7 — Fine-tune around the Phase 6 winner.

Winner so far (DD-constrained):
  ema_prin_len=35 + st_atr=14 + tick_buffer=0 + BO+07-08
  PnL $79,815 / DD $2,286 / WR 41.2% / PF 1.68

Levers to explore around this anchor:
  - risk_per_trade fine band (cliffs at int(contracts) boundaries)
  - sl_max_points 41..50
  - blackout BO +01-02 addition
  - ema_prin_len 33..37 fine
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
BO_0102 = [
    {"active": True, "start_hour": 1, "start_minute": 0,
     "end_hour": 2, "end_minute": 0},
]


BEST_BASE = {"ema_prin_len": 35, "st_atr": 14, "tick_buffer": 0}


def run(label, overrides=None, blackouts=None, risk=None):
    params = dict(SEED_PARAMS)
    params.update(BEST_BASE)
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
    print("=" * 140)
    print("Phase 7 — Fine-tune around Phase 6 winner")
    print("Anchor: ema=35 + st_atr=14 + tick_buffer=0 + BO+07-08")
    print("        PnL $79,815 / DD $2,286 / WR 41.2% / PF 1.68")
    print("=" * 140)

    print("\n--- 7A. risk_per_trade fine sweep (seed=0.006) ---")
    for r_pct in [0.55, 0.58, 0.60, 0.62, 0.63, 0.64, 0.65, 0.66, 0.68, 0.70, 0.72, 0.75, 0.80]:
        run(f"risk={r_pct}%", risk=r_pct / 100)

    print("\n--- 7B. sl_max_points around seed=41 ---")
    for v in [38, 40, 41, 42, 43, 44, 45, 46, 48, 50]:
        run(f"sl_max_points={v}", {"sl_max_points": v})

    print("\n--- 7C. ema_prin_len fine around 35 ---")
    for v in [33, 34, 35, 36, 37, 38, 40, 45]:
        run(f"ema_prin_len={v}", {"ema_prin_len": v})

    print("\n--- 7D. Add BO +01-02 ---")
    run("base (BO+07-08 only)",  {})
    run("base + BO+01-02",       {}, blackouts=SEED_BLACKOUTS + BO_0708 + BO_0102)
    run("base only BO+01-02",    {}, blackouts=SEED_BLACKOUTS + BO_0102)

    print("\n--- 7E. st_atr fine ---")
    for v in [10, 12, 14, 16, 18]:
        run(f"st_atr={v}", {"st_atr": v})

    print("\n--- 7F. ut_atr_period combined ---")
    for v in [7, 10, 14]:
        run(f"ut_atr_period={v}", {"ut_atr_period": v})

    print("\n--- 7G. ema_sec_len around 20 (still optimal in P4) ---")
    for v in [15, 18, 20, 22, 25]:
        run(f"ema_sec_len={v}", {"ema_sec_len": v})

    print("\n--- 7H. Final Pareto candidates ---")
    print("Tweak each direction from anchor by ONE param to map the local Pareto frontier:")
    # cross combos to look for cliff shifts
    for r_pct in [0.62, 0.63, 0.65, 0.66]:
        for v in [41, 43, 45]:
            run(f"risk={r_pct}% + sl_max={v}", {"sl_max_points": v}, risk=r_pct / 100)


if __name__ == "__main__":
    main()
