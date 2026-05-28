"""Sweep 08 — risk_per_trade fine sweep on top Pareto candidates.

Top picks from Sweep 07 (max_contracts=20 LOCKED):
  TOP_A:   sig60_hw35 + mor 6-9, mid 11-13, 14h30-15  → $74,911 / DD $3,508
  TOP_A2:  sig60_hw35 + mor 6-9, mid 11-14, 14h30-15  → $72,870 / DD $2,946 (best PnL+DD)
  TOP_B:   sig50_hw30 + mor 6-9, mid 11-14, 14h30-15  → $71,335 / DD $2,761 (best DD)
  TOP_C:   mf31       + mor 6-9, mid 11-14, 14h30-15  → $69,411 / DD $2,792

Sweep risk_per_trade ∈ {0.35, 0.40, 0.45, 0.50 (seed), 0.55, 0.60} on each.

Goal: find the risk × candidate that maximises PnL while keeping DD ≤ seed=$3,557.

Note: max_contracts=20 is hard-locked by the user. As risk rises, more trades
hit the cap, so PnL won't scale fully linearly.
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
    "TOP_A":  {"params": {"hma_pol_bars": 5, "sig_extreme": 60, "hw_extreme": 35},
               "blackouts": [CLOSE, (6,0,9,0), (11,0,13,0), (14,30,15,0)]},
    "TOP_A2": {"params": {"hma_pol_bars": 5, "sig_extreme": 60, "hw_extreme": 35},
               "blackouts": [CLOSE, (6,0,9,0), (11,0,14,0), (14,30,15,0)]},
    "TOP_B":  {"params": {"hma_pol_bars": 5, "sig_extreme": 50, "hw_extreme": 30},
               "blackouts": [CLOSE, (6,0,9,0), (11,0,14,0), (14,30,15,0)]},
    "TOP_C":  {"params": {"hma_pol_bars": 5, "sig_extreme": 60, "hw_extreme": 35, "mf_length": 31},
               "blackouts": [CLOSE, (6,0,9,0), (11,0,14,0), (14,30,15,0)]},
}

RISK_GRID = [0.0030, 0.0035, 0.0040, 0.0045, 0.0050, 0.0055, 0.0060, 0.0065]


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
    print(f"{label:<70s} {fmt_summary(s)}")
    return s


if __name__ == "__main__":
    results = []
    print("=" * 100)
    print("SWEEP 08 — risk × candidate")
    print("=" * 100)

    for name, cand in CANDIDATES.items():
        print()
        print(f"========== {name} ==========")
        for r in RISK_GRID:
            results.append(run(f"{name} | risk={r*100:.2f}%", cand, r))

    print()
    print("=" * 100)
    print("TOP-15 by PnL (no DD constraint)")
    print("=" * 100)
    for r in sorted(results, key=lambda x: -x["net_pnl"])[:15]:
        print(f"  {r['label']:<70s}  PnL=${r['net_pnl']:>9,.0f} | DD=${r['max_dd_$']:>6,.0f} | N={r['trades']}")

    print()
    print("TOP-15 by PnL with DD <= $3,557 (seed budget)")
    qualified = [r for r in results if r["max_dd_$"] <= 3557]
    for r in sorted(qualified, key=lambda x: -x["net_pnl"])[:15]:
        print(f"  {r['label']:<70s}  PnL=${r['net_pnl']:>9,.0f} | DD=${r['max_dd_$']:>6,.0f} | N={r['trades']}")

    print()
    print("TOP-15 by PnL with DD <= $3,000")
    tight = [r for r in results if r["max_dd_$"] <= 3000]
    for r in sorted(tight, key=lambda x: -r["net_pnl"])[:15]:
        print(f"  {r['label']:<70s}  PnL=${r['net_pnl']:>9,.0f} | DD=${r['max_dd_$']:>6,.0f} | N={r['trades']}")

    print()
    print("TOP-15 by PnL with DD <= $2,800")
    super_tight = [r for r in results if r["max_dd_$"] <= 2800]
    for r in sorted(super_tight, key=lambda x: -r["net_pnl"])[:15]:
        print(f"  {r['label']:<70s}  PnL=${r['net_pnl']:>9,.0f} | DD=${r['max_dd_$']:>6,.0f} | N={r['trades']}")
