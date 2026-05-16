"""Sweep 05 — Hour & day-of-week analysis on the new v2 baseline.

New v2 baseline = prev winner overrides
                + block_loss_exit_before_partial=True
                + hma1_len=9
                + max_sl_points=100
                + tick_buffer=1
                (only 22-23:59 blackout active)

Print hour bucket + dow bucket of the active trades to identify toxic hours.
"""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from scripts.goals._shared.harness import run_backtest, summarize, fmt_summary
from scripts.goals._shared.engine_settings import ui_default_engine_settings
from scripts.goals._shared.analysis import (
    bucket_by_hour, bucket_by_dow, print_hour_table, print_dow_table
)

from _campaign import (
    STRATEGY, SYMBOL, INTERVAL, START, END, INITIAL_EQUITY, MAX_CONTRACTS,
    PREV_WINNER_OVERRIDES, PREV_WINNER_RISK, pdd,
)

ES = ui_default_engine_settings(STRATEGY)
V2_BASELINE = dict(PREV_WINNER_OVERRIDES)
V2_BASELINE["block_loss_exit_before_partial"] = True
V2_BASELINE["hma1_len"] = 9
V2_BASELINE["max_sl_points"] = 100.0
V2_BASELINE["tick_buffer"] = 1


if __name__ == "__main__":
    print("=" * 110)
    print("Sweep 05 — Hour/DOW analysis on v2 baseline")
    print(f"Overrides: {V2_BASELINE}")
    print("=" * 110)

    r = run_backtest(
        strategy_name=STRATEGY, symbol=SYMBOL, interval=INTERVAL,
        start=START, end=END, strategy_params=V2_BASELINE,
        initial_equity=INITIAL_EQUITY, risk_per_trade=PREV_WINNER_RISK,
        max_contracts=MAX_CONTRACTS, engine_settings=ES,
    )
    s = summarize(r)
    print(f"\nv2 baseline: {fmt_summary(s)}  P/DD={pdd(s['net_pnl'], s['max_dd_$']):.2f}\n")

    print("HOUR BUCKETS")
    print_hour_table(bucket_by_hour(r["trades"]))
    print()
    print("DAY-OF-WEEK BUCKETS")
    print_dow_table(bucket_by_dow(r["trades"]))
