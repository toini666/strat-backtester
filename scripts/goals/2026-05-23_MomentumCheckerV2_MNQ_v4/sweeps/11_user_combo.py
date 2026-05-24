"""Phase 11 — Test the user's literal hypothesis combo.

The user explicitly described:
  "peut-être en réduisant le look-back ET en mettant un minimum de stop loss"

Phase 1 tested each independently. lb=2 alone blew DD to $4,770 because
tight SLs → giant positions → giant $ SL hits. The floor was supposed
to PREVENT that — so the combo lb ∈ {1, 2} × min_pct ∈ {0.05+, ...}
is the discriminating test that proves whether the user's hypothesis
is structurally sound.

Test against BOTH seed and the WINNER anchor.
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


WINNER_BASE = {
    "ema_prin_len": 34, "ema_sec_len": 18, "st_atr": 14,
    "tick_buffer": 0, "sl_max_points": 42,
}


def run(label, base_params, overrides, blackouts, risk):
    params = dict(SEED_PARAMS); params.update(base_params); params.update(overrides)
    result = run_backtest(
        strategy_name=STRATEGY, symbol=SYMBOL, interval=INTERVAL,
        start=START, end=END, strategy_params=params,
        initial_equity=INITIAL_EQUITY, risk_per_trade=risk,
        max_contracts=MAX_CONTRACTS,
        engine_settings=make_engine_settings(blackouts=blackouts),
    )
    s = summarize(result); s["label"] = label
    print(f"{label:<60s} {fmt_summary(s)}")
    return s


def main():
    print("=" * 140)
    print("Phase 11 — User hypothesis: short lookback + min_pct floor")
    print("=" * 140)

    print("\n--- 11A. SEED anchor — sl_lookback × sl_min_pct ---")
    for lb in [1, 2]:
        for mp in [0.05, 0.075, 0.10, 0.125, 0.15, 0.20]:
            run(f"SEED lb={lb} mp={mp}", {}, {"sl_lookback": lb, "sl_min_pct": mp},
                SEED_BLACKOUTS, SEED_RISK)

    print("\n--- 11B. WINNER anchor — sl_lookback × sl_min_pct ---")
    for lb in [1, 2, 3]:
        for mp in [0.05, 0.075, 0.10, 0.125, 0.15, 0.20]:
            run(f"WIN lb={lb} mp={mp}", WINNER_BASE,
                {"sl_lookback": lb, "sl_min_pct": mp},
                SEED_BLACKOUTS + BO_0708, 0.00625)

    print("\n--- 11C. WINNER reference (sanity) ---")
    run("WIN reference", WINNER_BASE, {}, SEED_BLACKOUTS + BO_0708, 0.00625)


if __name__ == "__main__":
    main()
