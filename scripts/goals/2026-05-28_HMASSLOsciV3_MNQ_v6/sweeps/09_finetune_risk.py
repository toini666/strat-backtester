"""Sweep 09 — fine-tune risk on TOP_C and TOP_A2 (the two best Pareto candidates).

Sweep 08 showed:
  TOP_C @ 0.60% → PnL=$80,709 / DD=$3,236  (best PnL+DD Pareto)
  TOP_C @ 0.55% → PnL=$76,262 / DD=$3,075
  TOP_A2 @ 0.55% → PnL=$79,522 / DD=$3,406

Fine grid: 0.525 - 0.625 by 0.025 on both.
"""

from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1]))

from _shared.harness import run_backtest, summarize, fmt_summary  # noqa: E402
from _campaign import (  # noqa: E402
    STRATEGY, SYMBOL, INTERVAL, START, END, INITIAL_EQUITY, MAX_CONTRACTS,
    SEED_PARAMS, make_engine_settings,
)


CLOSE = (22, 0, 23, 59)

CANDIDATES = {
    "TOP_A2": {"params": {"hma_pol_bars": 5, "sig_extreme": 60, "hw_extreme": 35},
               "blackouts": [CLOSE, (6,0,9,0), (11,0,14,0), (14,30,15,0)]},
    "TOP_B":  {"params": {"hma_pol_bars": 5, "sig_extreme": 50, "hw_extreme": 30},
               "blackouts": [CLOSE, (6,0,9,0), (11,0,14,0), (14,30,15,0)]},
    "TOP_C":  {"params": {"hma_pol_bars": 5, "sig_extreme": 60, "hw_extreme": 35, "mf_length": 31},
               "blackouts": [CLOSE, (6,0,9,0), (11,0,14,0), (14,30,15,0)]},
}


def run(label, cand, risk):
    p = dict(SEED_PARAMS)
    p.update(cand["params"])
    es = make_engine_settings(cand["blackouts"])
    res = run_backtest(
        strategy_name=STRATEGY,
        symbol=SYMBOL,
        interval=INTERVAL,
        start=START,
        end=END,
        initial_equity=INITIAL_EQUITY,
        risk_per_trade=risk,
        max_contracts=MAX_CONTRACTS,
        strategy_params=p,
        engine_settings=es,
    )
    s = summarize(res)
    s["label"] = label
    s["risk"] = risk
    print(f"{label:<55s} {fmt_summary(s)}")
    return s


if __name__ == "__main__":
    results = []
    for name, cand in CANDIDATES.items():
        print()
        print(f"========== {name} ==========")
        for r in [0.00525, 0.00550, 0.00575, 0.00600, 0.00625]:
            results.append(run(f"{name} | risk={r*100:.3f}%", cand, r))

    print()
    print("=" * 100)
    print("STRICT PARETO  (PnL >= seed=$63,143 AND DD < seed=$3,557)")
    print("=" * 100)
    for r in sorted(results, key=lambda x: -x["net_pnl"]):
        if r["net_pnl"] >= 63143 and r["max_dd_$"] < 3557:
            print(f"  ✓ {r['label']:<55s}  PnL=${r['net_pnl']:>9,.0f} (+${r['net_pnl']-63143:,.0f}) | "
                  f"DD=${r['max_dd_$']:>6,.0f} ({r['max_dd_$']-3557:+,.0f})")
