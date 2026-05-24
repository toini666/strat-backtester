"""Phase 6 — Combo lattice on Phase 1/4/5 survivors.

Phase 1 (SL geometry): tick_buffer=0 (+PnL +DD), sl_max_points=50 (+PnL +DD)
Phase 4 (point/indicator): ema_prin_len=35 (+PnL +WR), st_atr=14 (+PnL),
                           pts_hma_slow=0 (+WR slight, -PnL slight),
                           ut_atr_period=14 (~neutral), max_candle_pct=0.35 (~neutral)
Phase 5 (blackouts):       +07:00-08:00 (+PnL -DD +WR -- THE BIG WIN)

Combos to test (additive hypothesis): seed + BO_07_08 + ema_prin=35 → likely
best base. Then add second-order tweaks.
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


BO_PLUS_0708 = SEED_BLACKOUTS + [
    {"active": True, "start_hour": 7, "start_minute": 0,
     "end_hour": 8, "end_minute": 0}
]
BO_PLUS_0708_AND_0102 = BO_PLUS_0708 + [
    {"active": True, "start_hour": 1, "start_minute": 0,
     "end_hour": 2, "end_minute": 0}
]


def run(label, overrides=None, blackouts=None, risk=None):
    params = dict(SEED_PARAMS)
    if overrides:
        params.update(overrides)
    bo = blackouts if blackouts is not None else SEED_BLACKOUTS
    r = risk if risk is not None else SEED_RISK
    result = run_backtest(
        strategy_name=STRATEGY, symbol=SYMBOL, interval=INTERVAL,
        start=START, end=END, strategy_params=params,
        initial_equity=INITIAL_EQUITY, risk_per_trade=r,
        max_contracts=MAX_CONTRACTS,
        engine_settings=make_engine_settings(blackouts=bo),
    )
    s = summarize(result); s["label"] = label
    print(f"{label:<55s} {fmt_summary(s)}")
    return s


def main():
    print("=" * 140)
    print("Phase 6 — Combo lattice on survivors")
    print("Seed: PnL $75,132 / DD $2,420 / WR 39.6%")
    print("=" * 140)

    print("\n--- 6A. SEED + each single lever (sanity) ---")
    run("SEED",                            {})
    run("ema_prin_len=35",                  {"ema_prin_len": 35})
    run("BO +07-08",                        {}, blackouts=BO_PLUS_0708)
    run("st_atr=14",                        {"st_atr": 14})
    run("pts_hma_slow=0",                   {"pts_hma_slow": 0})
    run("ut_atr_period=14",                 {"ut_atr_period": 14})

    print("\n--- 6B. Dual combos ---")
    run("ema=35 + BO0708",                  {"ema_prin_len": 35}, blackouts=BO_PLUS_0708)
    run("ema=35 + st_atr=14",               {"ema_prin_len": 35, "st_atr": 14})
    run("ema=35 + pts_hma_slow=0",          {"ema_prin_len": 35, "pts_hma_slow": 0})
    run("BO0708 + st_atr=14",               {"st_atr": 14}, blackouts=BO_PLUS_0708)
    run("BO0708 + pts_hma_slow=0",          {"pts_hma_slow": 0}, blackouts=BO_PLUS_0708)
    run("ema=35 + ut_atr=14",               {"ema_prin_len": 35, "ut_atr_period": 14})

    print("\n--- 6C. Triple combos ---")
    run("ema=35 + BO0708 + st_atr=14",      {"ema_prin_len": 35, "st_atr": 14}, blackouts=BO_PLUS_0708)
    run("ema=35 + BO0708 + pts_hma_slow=0", {"ema_prin_len": 35, "pts_hma_slow": 0}, blackouts=BO_PLUS_0708)
    run("ema=35 + BO0708 + ut_atr=14",      {"ema_prin_len": 35, "ut_atr_period": 14}, blackouts=BO_PLUS_0708)
    run("BO0708 + st_atr=14 + pts_hma_slow=0",
        {"st_atr": 14, "pts_hma_slow": 0}, blackouts=BO_PLUS_0708)

    print("\n--- 6D. Quad combos ---")
    run("ema=35 + BO0708 + st_atr=14 + pts_hma_slow=0",
        {"ema_prin_len": 35, "st_atr": 14, "pts_hma_slow": 0}, blackouts=BO_PLUS_0708)
    run("ema=35 + BO0708 + st_atr=14 + ut_atr=14",
        {"ema_prin_len": 35, "st_atr": 14, "ut_atr_period": 14}, blackouts=BO_PLUS_0708)
    run("ema=35 + BO0708 + st_atr=14 + pts_hma_slow=0 + ut_atr=14",
        {"ema_prin_len": 35, "st_atr": 14, "pts_hma_slow": 0, "ut_atr_period": 14},
        blackouts=BO_PLUS_0708)

    print("\n--- 6E. Add risk geometry (tick_buffer=0, sl_max_points=50) on the best combo ---")
    BEST = {"ema_prin_len": 35, "st_atr": 14}
    run("BEST + tick_buffer=0",             {**BEST, "tick_buffer": 0}, blackouts=BO_PLUS_0708)
    run("BEST + sl_max_points=50",          {**BEST, "sl_max_points": 50}, blackouts=BO_PLUS_0708)
    run("BEST + tb=0 + slmax=50",           {**BEST, "tick_buffer": 0, "sl_max_points": 50}, blackouts=BO_PLUS_0708)
    run("BEST + rr_tp=2.25",                {**BEST, "rr_tp": 2.25}, blackouts=BO_PLUS_0708)
    run("BEST + max_candle=0.35",           {**BEST, "max_candle_pct": 0.35}, blackouts=BO_PLUS_0708)


if __name__ == "__main__":
    main()
