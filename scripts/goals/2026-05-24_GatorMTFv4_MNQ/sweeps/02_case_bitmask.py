"""Sweep 2 — Case A/B/C/D bitmask (16 combos) × small final_rr grid.

Cases A/B = same-canal (M7 vert + M1 vert → long, etc.) — high-prob trades.
Cases C/D = counter-canal (M7 vs M1) with sig-extreme gate — lower prob.

The seed has all 4 cases on. Turning off the weakest case is a structural
DD cut that costs PnL only if that case carries edge.

~ 16 × 4 = 64 sims.
"""

from __future__ import annotations

import sys
from itertools import product
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.goals._shared.harness import run_backtest, summarize, fmt_summary
from scripts.goals._shared.engine_settings import ui_default_engine_settings
from sweeps._campaign import (
    SEED_PARAMS, SEED_RISK, SEED_AUTO_CLOSE, SEED_BLACKOUTS,
    START, END, SYMBOL, INTERVAL, STRATEGY,
    INITIAL_EQUITY, MAX_CONTRACTS,
)


def _engine():
    es = ui_default_engine_settings(STRATEGY)
    for w in es.blackout_windows:
        w.active = (w.start_hour, w.start_minute, w.end_hour, w.end_minute) in [
            (sh, sm, eh, em) for sh, sm, eh, em in SEED_BLACKOUTS
        ]
    es.auto_close_hour, es.auto_close_minute = SEED_AUTO_CLOSE
    return es


def run_one(label: str, **overrides):
    params = dict(SEED_PARAMS)
    params.update(overrides)
    r = run_backtest(
        strategy_name=STRATEGY,
        symbol=SYMBOL,
        interval=INTERVAL,
        start=START,
        end=END,
        strategy_params=params,
        initial_equity=INITIAL_EQUITY,
        risk_per_trade=SEED_RISK,
        max_contracts=MAX_CONTRACTS,
        engine_settings=_engine(),
    )
    s = summarize(r)
    print(f"{label:<55s} {fmt_summary(s)}")
    return s


def main():
    print("=" * 90)
    print("SWEEP 2 — CASE BITMASK × FINAL_RR")
    print("=" * 90)

    results = []
    final_rrs = [1.0, 1.5, 2.0, 2.5]

    # 16 bitmask combos: skip the empty one (no cases = no trades)
    bitmask_combos = list(product([False, True], repeat=4))[1:]

    for a, b, c, d in bitmask_combos:
        for rr in final_rrs:
            mask_str = "".join("1" if x else "0" for x in (a, b, c, d))
            label = f"ABCD={mask_str} rr={rr}"
            s = run_one(
                label,
                case_a_on=a, case_b_on=b, case_c_on=c, case_d_on=d,
                final_rr=rr,
            )
            results.append((label, s, mask_str, rr))

    print()
    print("=" * 90)
    print("TOP RESULTS (DD ≤ $2,500, ranked by PnL)")
    print("=" * 90)
    ok = [(l, s) for l, s, _, _ in results if s["max_dd_$"] <= 2500.0]
    ok.sort(key=lambda x: -x[1]["net_pnl"])
    for l, s in ok[:30]:
        print(f"  {l:<50s} {fmt_summary(s)}")

    print()
    print("TOP 20 BY PnL (DD unconstrained)")
    by_pnl = sorted(results, key=lambda x: -x[1]["net_pnl"])
    for l, s, _, _ in by_pnl[:20]:
        print(f"  {l:<50s} {fmt_summary(s)}")


if __name__ == "__main__":
    main()
