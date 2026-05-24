"""Phase 7A — hour-of-day + day-of-week analysis at new best config.

The v1 hour ranking is invalid for v2 (different RR, SSL, SL, amp_mult, cooldown).
Re-run on the new best config to find losing/winning hours, then build
cumulative blackout bundles in Phase 7B.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.goals._shared.harness import run_backtest, summarize, fmt_summary
from scripts.goals._shared.engine_settings import ui_default_engine_settings
from scripts.goals._shared.analysis import (
    bucket_by_hour, bucket_by_dow, print_hour_table, print_dow_table,
)
from sweeps._campaign import (
    V1_WINNER_PARAMS, SWEEP_RISK, AUTO_CLOSE,
    START, END, SYMBOL, INTERVAL, STRATEGY,
    INITIAL_EQUITY, MAX_CONTRACTS,
)

BEST_CONFIG = {
    "amp_mult": 1.5, "hma1_len": 13, "hma2_len": 21,
    "case_a_on": True, "case_b_on": True,
    "case_c_on": False, "case_d_on": True,
    "final_rr": 1.5, "cooldown_bars": 90,
    "sl_lookback": 15, "tick_buffer": 6,
    "ssl_len": 20, "ssl_mult": 0.20,
}


def _es_no_blackouts():
    es = ui_default_engine_settings(STRATEGY)
    for w in es.blackout_windows:
        w.active = False
    es.auto_close_hour, es.auto_close_minute = AUTO_CLOSE
    return es


def main():
    print("=" * 100)
    print("PHASE 7A — hour-of-day + day-of-week analysis at new best config")
    print("=" * 100)
    es = _es_no_blackouts()
    SEED = dict(V1_WINNER_PARAMS)
    SEED.update(BEST_CONFIG)

    r = run_backtest(
        strategy_name=STRATEGY,
        symbol=SYMBOL, interval=INTERVAL,
        start=START, end=END,
        strategy_params=SEED,
        initial_equity=INITIAL_EQUITY,
        risk_per_trade=SWEEP_RISK,
        max_contracts=MAX_CONTRACTS,
        engine_settings=es,
    )
    s = summarize(r)
    print(f"Base: {fmt_summary(s)}")
    print()

    trades = r["trades"]
    print("--- Hour buckets (entry_time hour, Brussels) ---")
    by_hour = bucket_by_hour(trades)
    print_hour_table(by_hour)
    print()

    losers = sorted(
        [(h, d) for h, d in by_hour.items() if d["total"] < 0],
        key=lambda x: x[1]["total"]
    )
    print("Losing hours (sorted by total $):")
    for h, d in losers:
        print(f"  H{h:02d}: total=${d['total']:>+8,.0f}  avg=${d['avg']:>+6,.0f}  N={d['n']:>4}  WR={d['win_rate']:.0f}%")

    print()
    print("--- Day-of-week buckets ---")
    by_dow = bucket_by_dow(trades)
    print_dow_table(by_dow)


if __name__ == "__main__":
    main()
