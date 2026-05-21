"""Phase 6 — Indicator length sweeps (Alligator, ST, STC, EMA, HMA).

Each axis 1-D first to find local optima, then a few combos.

Skip known-dead: hma_pol_bars, ssl_mult.
Skip known-bad: amp_mult > 2.5 on MGC (backfires).

~50 sims.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

CAMPAIGN_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CAMPAIGN_DIR / "sweeps"))

from scripts.goals._shared.harness import run_backtest, summarize, fmt_summary  # noqa: E402

from _campaign import (  # noqa: E402
    BASELINE_PARAMS, END, INITIAL_EQUITY, INTERVAL, MAX_CONTRACTS,
    RISK_PER_TRADE, START, STRATEGY, SYMBOL, seed_engine,
)

ANCHOR_SL_MAX = float(os.environ.get("ANCHOR_SL_MAX", 100.0))
ANCHOR_RISK   = float(os.environ.get("ANCHOR_RISK", RISK_PER_TRADE))


def run(label, params, risk=ANCHOR_RISK):
    r = run_backtest(
        strategy_name=STRATEGY, symbol=SYMBOL, interval=INTERVAL,
        start=START, end=END,
        initial_equity=INITIAL_EQUITY, risk_per_trade=risk,
        max_contracts=MAX_CONTRACTS,
        engine_settings=seed_engine(),
        strategy_params=params,
    )
    s = summarize(r)
    s["label"] = label
    print(f"{label:<60s} {fmt_summary(s)}")
    return s


def main() -> int:
    print("=" * 110)
    print(f"PHASE 6 — Indicator lengths @ sl_max={ANCHOR_SL_MAX} r={ANCHOR_RISK*100:.3f}%")
    print("=" * 110)

    base = dict(BASELINE_PARAMS)
    base["sl_max_points"] = ANCHOR_SL_MAX

    print("\n--- 6A: EMA lengths (prin × sec) ---")
    for prin in [15, 20, 25, 30, 35, 40, 50]:
        for sec in [3, 5, 7, 9, 12]:
            p = dict(base)
            p["ema_prin_len"] = prin
            p["ema_sec_len"]  = sec
            run(f"ema_prin={prin:>3} ema_sec={sec:>2}", p)

    print("\n--- 6B: ST (atr × mult) ---")
    for atr in [7, 10, 14, 20]:
        for mult in [2.0, 2.5, 3.0, 3.5, 4.0]:
            p = dict(base)
            p["st_atr"]  = atr
            p["st_mult"] = mult
            run(f"st_atr={atr:>2} st_mult={mult}", p)

    print("\n--- 6C: STC params ---")
    for stcl in [8, 10, 12, 15]:
        for fast in [23, 32, 40]:
            p = dict(base)
            p["stc_length"]   = stcl
            p["stc_fast_len"] = fast
            run(f"stc_length={stcl} stc_fast_len={fast}", p)

    print("\n--- 6D: Alligator (jaw × teeth × lips) lengths ---")
    for jaw in [10, 13, 17, 21]:
        for teeth in [5, 8, 11]:
            p = dict(base)
            p["jaw_length"]   = jaw
            p["teeth_length"] = teeth
            run(f"jaw={jaw:>2} teeth={teeth:>2}", p)

    print("\n--- 6E: HMA lengths (h1, h2) ---")
    for h1 in [30, 42, 50]:
        for h2 in [63, 84, 105]:
            p = dict(base)
            p["hma1_len"] = h1
            p["hma2_len"] = h2
            run(f"hma1={h1} hma2={h2}", p)

    return 0


if __name__ == "__main__":
    sys.exit(main())
