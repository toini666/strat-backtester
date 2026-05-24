"""Phase 2b — TRUE SIG range reject (sig_range_reject).

This uses the new `sig_range_reject` param that rejects entries when
|sig| <= sig_level. Matches the user's "zone à éviter" intent.
Goal: increase WR by dropping median-SIG setups.
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


def run(label: str, overrides: dict):
    params = dict(SEED_PARAMS)
    params.update(overrides)
    result = run_backtest(
        strategy_name=STRATEGY,
        symbol=SYMBOL,
        interval=INTERVAL,
        start=START,
        end=END,
        strategy_params=params,
        initial_equity=INITIAL_EQUITY,
        risk_per_trade=SEED_RISK,
        max_contracts=MAX_CONTRACTS,
        engine_settings=make_engine_settings(),
    )
    s = summarize(result)
    s["label"] = label
    print(f"{label:<46s} {fmt_summary(s)}")
    return s


def main():
    print("=" * 130)
    print("Phase 2b — SIG range reject (true filter)")
    print("Seed: PnL $75,132 / DD $2,420 / WR 39.6%")
    print("=" * 130)

    print("\n--- sig_range_reject=True × sig_level ---")
    for lvl in [2, 3, 4, 5, 7, 8, 10, 12, 15, 18, 20, 25]:
        run(f"reject lvl={lvl}", {
            "sig_range_reject": True, "sig_level": lvl,
        })

    # Aim: pick the level that maximises (WR up, PnL stable, DD ≤ seed).


if __name__ == "__main__":
    main()
