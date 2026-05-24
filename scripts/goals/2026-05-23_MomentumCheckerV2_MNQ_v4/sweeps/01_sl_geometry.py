"""Phase 1 (highest-EV) — SL geometry sweep.

Hypothesis (user + baseline confirmed):
  - 60.3 % of seed trades hit SL.
  - The bottom 10 losers all hit the sl_max_points=41 cap (~38 points).
  - Many losing trades likely went the right way first before reversing
    into a too-wide SL.

Levers:
  - sl_lookback: how far back to find the SL anchor (seed=5).
  - sl_min_pct:  NEW. Floor on SL distance as a % of entry price.
  - sl_max_points: cap (seed=41).
  - tick_buffer: ticks added beyond the lookback extreme (seed=2).

Goal of this sweep: identify SL geometries that (a) increase WR
without (b) blowing the DD past $2,420 budget. Net PnL is acceptable
to soften here — combos will recover it later via lower risk fees.

Budget: ~60-80 sims.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from scripts.goals._shared.harness import run_backtest, summarize, fmt_summary
from sweeps._campaign import (
    END,
    INITIAL_EQUITY,
    INTERVAL,
    MAX_CONTRACTS,
    SEED_PARAMS,
    SEED_RISK,
    START,
    STRATEGY,
    SYMBOL,
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
    print("Phase 1 — SL geometry (1-D sweeps, then combos)")
    print("Seed: PnL $75,132 / DD $2,420 / WR 39.6% / SL_rate 60.3%")
    print("=" * 130)

    print("\n--- 1A. sl_lookback (seed=5) ---")
    for lb in [2, 3, 4, 5, 6, 7, 10]:
        run(f"sl_lookback={lb}", {"sl_lookback": lb})

    print("\n--- 1B. sl_min_pct (NEW, seed=0.0) ---")
    for mp in [0.0, 0.05, 0.075, 0.10, 0.125, 0.15, 0.175, 0.20, 0.25]:
        run(f"sl_min_pct={mp}", {"sl_min_pct": mp})

    print("\n--- 1C. sl_max_points (seed=41) — narrower caps ---")
    for mx in [20, 25, 30, 35, 38, 41, 45, 50]:
        run(f"sl_max_points={mx}", {"sl_max_points": mx})

    print("\n--- 1D. tick_buffer (seed=2) ---")
    for tb in [0, 1, 2, 3, 5]:
        run(f"tick_buffer={tb}", {"tick_buffer": tb})

    print("\n--- 1E. rr_tp (seed=2.5) — TP closer means more wins ---")
    for rr in [1.5, 1.75, 2.0, 2.25, 2.5, 2.75, 3.0]:
        run(f"rr_tp={rr}", {"rr_tp": rr})

    # Quick 2-D pilot: best 1-D survivors combined.
    print("\n--- 1F. lookback × sl_min_pct pilot ---")
    for lb in [3, 4, 5]:
        for mp in [0.0, 0.05, 0.10, 0.15]:
            run(f"lb={lb} min_pct={mp}", {"sl_lookback": lb, "sl_min_pct": mp})


if __name__ == "__main__":
    main()
