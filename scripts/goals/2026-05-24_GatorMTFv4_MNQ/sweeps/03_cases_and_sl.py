"""Sweep 3 — Case bitmask × SL/RR tuning on the best combo so far.

Uses TOP combo from sweep 2 as base — set those constants once we know.
For now, defaults to seed-with-rr=2/cd=120/amp=1.0 (most-promising guess).

Two scans:
  A. Case bitmask × top combo  (15 sims)
  B. sl_min_pct fine + entry_window_bars_trigger fine (12 sims)
  C. ssl_mult fine + trigger_tf joint  (24 sims)

Total ~50 sims.
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


# From sweep 2 winner: rr=2.0/cd=90/amp=1.0 → PnL=$21,240 / DD=$5,935.
BASE_OVERRIDES = {
    "final_rr": 2.0,
    "cooldown_bars": 90,
    "amp_mult": 1.0,
}


def _engine():
    es = ui_default_engine_settings(STRATEGY)
    for w in es.blackout_windows:
        w.active = (w.start_hour, w.start_minute, w.end_hour, w.end_minute) in [
            (sh, sm, eh, em) for sh, sm, eh, em in SEED_BLACKOUTS
        ]
    es.auto_close_hour, es.auto_close_minute = SEED_AUTO_CLOSE
    return es


def run_one(label, **overrides):
    params = dict(SEED_PARAMS)
    params.update(BASE_OVERRIDES)
    params.update(overrides)
    r = run_backtest(
        strategy_name=STRATEGY, symbol=SYMBOL, interval=INTERVAL,
        start=START, end=END,
        strategy_params=params,
        initial_equity=INITIAL_EQUITY, risk_per_trade=SEED_RISK,
        max_contracts=MAX_CONTRACTS,
        engine_settings=_engine(),
    )
    s = summarize(r)
    print(f"{label:<55s} {fmt_summary(s)}")
    return s


def main():
    print("=" * 90)
    print("SWEEP 3 — Cases × SL × ssl_mult around best combo")
    print(f"Base: {BASE_OVERRIDES}")
    print("=" * 90)
    results = []

    # A) Case bitmask (15 non-empty combos)
    print()
    print(">>> A. Case bitmask")
    for a, b, c, d in product([False, True], repeat=4):
        if not any([a, b, c, d]):
            continue
        mask = "".join("1" if x else "0" for x in (a, b, c, d))
        label = f"ABCD={mask}"
        s = run_one(label,
                    case_a_on=a, case_b_on=b, case_c_on=c, case_d_on=d)
        results.append((label, s))

    # B) SL fine
    print()
    print(">>> B. sl_min_pct + entry_window")
    for slp in [0.10, 0.20, 0.30, 0.45]:
        for ew in [2, 3, 5]:
            label = f"slp={slp} ew={ew}"
            s = run_one(label, sl_min_pct=slp, entry_window_bars_trigger=ew)
            results.append((label, s))

    # C) ssl_mult + trigger_tf
    print()
    print(">>> C. ssl_mult + trigger_tf_minutes")
    for sm in [0.15, 0.20, 0.25, 0.30]:
        for tf in [5, 7, 10, 15]:
            label = f"ssl_mult={sm} tf={tf}"
            s = run_one(label, ssl_mult=sm, trigger_tf_minutes=tf)
            results.append((label, s))

    print()
    print("=" * 90)
    print("TOP RESULTS — DD ≤ $2,500 by PnL")
    print("=" * 90)
    ok = [(l, s) for l, s in results if s["max_dd_$"] <= 2500.0]
    ok.sort(key=lambda x: -x[1]["net_pnl"])
    for l, s in ok[:30]:
        print(f"  {l:<50s} {fmt_summary(s)}")

    print()
    print("TOP RESULTS — DD ≤ $5,000 by PnL")
    ok5 = [(l, s) for l, s in results if s["max_dd_$"] <= 5000.0]
    ok5.sort(key=lambda x: -x[1]["net_pnl"])
    for l, s in ok5[:30]:
        print(f"  {l:<50s} {fmt_summary(s)}")

    print()
    print("BEST DD (top 15)")
    by_dd = sorted(results, key=lambda x: x[1]["max_dd_$"])
    for l, s in by_dd[:15]:
        print(f"  {l:<50s} {fmt_summary(s)}")


if __name__ == "__main__":
    main()
