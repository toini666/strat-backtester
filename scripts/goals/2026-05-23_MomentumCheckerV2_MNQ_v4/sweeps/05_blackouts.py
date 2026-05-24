"""Phase 5 — Blackout tuning.

Baseline hour analysis identified:
  H=01 toxic   (39 trades, -$1,087, 26% WR)
  H=23 toxic   ( 4 trades, -$1,039,  0% WR)  -- low N, possibly noise
  H=00 marginal (66 trades, +$2,927, 35% WR)
  H=07 marginal (48 trades, +$1,374, 33% WR)

Seed blackouts (active):
  09:00-10:00, 13:00-14:30, 17:00-23:59, 22:00-23:59

Test:
  - Add 01:00-02:00 blackout
  - Add 00:00-01:00 (drop H=00 too)
  - Add 23:00-00:00 (drop H=23 wall-clock)
  - Various combinations
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


def run(label, blackouts):
    result = run_backtest(
        strategy_name=STRATEGY, symbol=SYMBOL, interval=INTERVAL,
        start=START, end=END, strategy_params=SEED_PARAMS,
        initial_equity=INITIAL_EQUITY, risk_per_trade=SEED_RISK,
        max_contracts=MAX_CONTRACTS,
        engine_settings=make_engine_settings(blackouts=blackouts),
    )
    s = summarize(result); s["label"] = label
    print(f"{label:<46s} {fmt_summary(s)}")
    return s


def add_window(blackouts, sh, sm, eh, em):
    """Return blackouts list with an extra active window appended."""
    return blackouts + [{"active": True, "start_hour": sh, "start_minute": sm,
                         "end_hour": eh, "end_minute": em}]


def main():
    print("=" * 130)
    print("Phase 5 — Blackout tuning")
    print("Seed: PnL $75,132 / DD $2,420 / WR 39.6%")
    print("=" * 130)

    # Baseline (seed blackouts only)
    run("SEED", SEED_BLACKOUTS)

    # Hour ranges to test
    print("\n--- 5A. Single new windows ---")
    for sh, sm, eh, em, lbl in [
        ( 1, 0,  2, 0, "+01:00-02:00"),
        ( 0, 0,  2, 0, "+00:00-02:00"),
        ( 0, 0,  1, 0, "+00:00-01:00"),
        (23, 0, 23, 59, "+23:00-23:59"),
        ( 7, 0,  8, 0, "+07:00-08:00"),
        (10, 0, 11, 0, "+10:00-11:00"),
        (14, 30, 15, 30, "+14:30-15:30 (extend lunch)"),
    ]:
        run(lbl, add_window(SEED_BLACKOUTS, sh, sm, eh, em))

    print("\n--- 5B. Multi-window combos ---")
    bo1 = add_window(SEED_BLACKOUTS, 1, 0, 2, 0)
    run("seed+01-02", bo1)
    bo2 = add_window(bo1, 23, 0, 23, 59)
    run("seed+01-02+23-23:59", bo2)
    bo3 = add_window(bo2, 0, 0, 1, 0)
    run("seed+00-02+23-23:59", bo3)

    print("\n--- 5C. Replace 17-23:59 with 17-22 (free up H=21 already; check 17-21 only) ---")
    alt = []
    for bo in SEED_BLACKOUTS:
        if bo["start_hour"] == 17 and bo["end_hour"] == 23:
            alt.append({"active": True, "start_hour": 17, "start_minute": 0,
                        "end_hour": 22, "end_minute": 0})
        else:
            alt.append(dict(bo))
    run("17-22 instead of 17-23:59", alt)


if __name__ == "__main__":
    main()
