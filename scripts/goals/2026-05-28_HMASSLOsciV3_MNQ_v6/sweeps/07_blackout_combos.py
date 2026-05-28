"""Sweep 07 — combine the best blackout slices.

Best slices from 06:
  - morning 6-9 (PnL boost vs 5-9)
  - midday 11-14 wide (DD cut)
  - 14h30-15h tight (same DD as seed, PnL bumped)
  - Combined morning + midday tweaks

Also test on candidates B (sig=50 hw=30) and C (mf=31) to see if their DD edge
translates with the better blackout stack.
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
    SEED_RISK, SEED_PARAMS, make_engine_settings,
)


CHAMP_A = {"hma_pol_bars": 5, "sig_extreme": 60, "hw_extreme": 35}  # top PnL
CHAMP_B = {"hma_pol_bars": 5, "sig_extreme": 50, "hw_extreme": 30}  # balanced
CHAMP_C = {"hma_pol_bars": 5, "sig_extreme": 60, "hw_extreme": 35, "mf_length": 31}  # DD-cut


def run(label, active_windows, champ_params):
    es = make_engine_settings(active_windows)
    p = dict(SEED_PARAMS)
    p.update(champ_params)
    res = run_backtest(
        strategy_name=STRATEGY,
        symbol=SYMBOL,
        interval=INTERVAL,
        start=START,
        end=END,
        initial_equity=INITIAL_EQUITY,
        risk_per_trade=SEED_RISK,
        max_contracts=MAX_CONTRACTS,
        strategy_params=p,
        engine_settings=es,
    )
    s = summarize(res)
    s["label"] = label
    print(f"{label:<70s} {fmt_summary(s)}")
    return s


# Blackout candidate stacks (active windows only — minimal 22-23:59 stays)
CLOSE = (22, 0, 23, 59)

BLACKOUTS = {
    "seed (5-9, 11-13, 14-15)": [CLOSE, (5,0,9,0), (11,0,13,0), (14,0,15,0)],
    "mor 6-9, mid 11-13, 14-15": [CLOSE, (6,0,9,0), (11,0,13,0), (14,0,15,0)],
    "mor 6-9, mid 11-14, no 14-15": [CLOSE, (6,0,9,0), (11,0,14,0)],
    "mor 6-9, mid 11-14, 14h30-15": [CLOSE, (6,0,9,0), (11,0,14,0), (14,30,15,0)],
    "mor 7-9, mid 11-13, 14-15": [CLOSE, (7,0,9,0), (11,0,13,0), (14,0,15,0)],
    "mor 8-9, mid 11-13, 14-15": [CLOSE, (8,0,9,0), (11,0,13,0), (14,0,15,0)],
    "mor 6-9, mid 11-12+12-14, no 14-15": [CLOSE, (6,0,9,0), (11,0,12,0), (12,0,14,0)],  # same as 11-14
    "mor 6-9, mid 11-13, 14h30-15": [CLOSE, (6,0,9,0), (11,0,13,0), (14,30,15,0)],
    "mor 6-9, mid 12-13, 14-15": [CLOSE, (6,0,9,0), (12,0,13,0), (14,0,15,0)],
    "mor 6-9, no mid, no afternoon": [CLOSE, (6,0,9,0)],
    "ONLY close (22-23:59)": [CLOSE],
    "mor 6-9, mid 11-13, no afternoon": [CLOSE, (6,0,9,0), (11,0,13,0)],
}


if __name__ == "__main__":
    print("=" * 100)
    print("SWEEP 07 — blackout × candidate combos")
    print("=" * 100)

    all_results = {}
    for champ_name, champ in [("A=sig60_hw35", CHAMP_A), ("B=sig50_hw30", CHAMP_B), ("C=mf31", CHAMP_C)]:
        print()
        print(f"========== CHAMP {champ_name} ==========")
        all_results[champ_name] = []
        for lab, wins in BLACKOUTS.items():
            r = run(f"{champ_name} | {lab}", wins, champ)
            r["champ"] = champ_name
            all_results[champ_name].append(r)

    print()
    print("=" * 100)
    print("OVERALL TOP-15 by PnL")
    print("=" * 100)
    flat = [r for rs in all_results.values() for r in rs]
    for r in sorted(flat, key=lambda x: -x["net_pnl"])[:15]:
        print(f"  {r['label']:<70s}  PnL=${r['net_pnl']:>9,.0f} | DD=${r['max_dd_$']:>6,.0f} | N={r['trades']}")

    print()
    print("OVERALL TOP-15 by DD (PnL >= $60k)")
    qualified = [r for r in flat if r["net_pnl"] >= 60000]
    for r in sorted(qualified, key=lambda x: x["max_dd_$"])[:15]:
        print(f"  {r['label']:<70s}  PnL=${r['net_pnl']:>9,.0f} | DD=${r['max_dd_$']:>6,.0f} | N={r['trades']}")

    print()
    print("STRICT PARETO  (PnL >= seed=$63,143 AND DD < seed=$3,557)")
    for r in flat:
        if r["net_pnl"] >= 63143 and r["max_dd_$"] < 3557:
            print(f"  ✓ {r['label']:<70s}  PnL=${r['net_pnl']:>9,.0f} (+${r['net_pnl']-63143:,.0f}) | "
                  f"DD=${r['max_dd_$']:>6,.0f} ({r['max_dd_$']-3557:+,.0f})")
