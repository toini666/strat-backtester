"""Sweep 01 — Baseline.

Reproduces the previous campaign's WINNER overrides (hma2_len=34, hw_range_on=True)
with ONLY the default 22:00-23:59 blackout active (UI default for HMASSLOsciV3).
This is the starting reference of the v2 campaign.

Also runs:
- Pure v3 defaults (no overrides) on TF 7m as second baseline.
- TF 10m comparator for both configs.
"""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from scripts.goals._shared.harness import bench
from scripts.goals._shared.engine_settings import ui_default_engine_settings
from scripts.goals._shared.analysis import bucket_by_hour, bucket_by_dow, print_hour_table, print_dow_table
from scripts.goals._shared.harness import run_backtest, summarize, fmt_summary

from _campaign import (
    STRATEGY, SYMBOL, START, END, INITIAL_EQUITY, MAX_CONTRACTS,
    PREV_WINNER_OVERRIDES, PREV_WINNER_RISK, pdd,
)


def run_one(label, interval, params, risk):
    es = ui_default_engine_settings(STRATEGY)  # only 22-23:59 active
    r = run_backtest(
        strategy_name=STRATEGY, symbol=SYMBOL, interval=interval,
        start=START, end=END, strategy_params=params,
        initial_equity=INITIAL_EQUITY, risk_per_trade=risk,
        max_contracts=MAX_CONTRACTS, engine_settings=es,
    )
    s = summarize(r)
    s["label"] = label
    s["trades_raw"] = r["trades"]
    print(f"{label:<50s} {fmt_summary(s)}  P/DD={pdd(s['net_pnl'], s['max_dd_$']):.2f}")
    return s


if __name__ == "__main__":
    print("=" * 100)
    print("Sweep 01 — Baseline (only blackout 22:00-23:59 active)")
    print("=" * 100)

    results = []
    # Previous winner overrides applied
    results.append(run_one("prev_winner_overrides @ 7m r=0.52%",
                           "7m", PREV_WINNER_OVERRIDES, PREV_WINNER_RISK))
    results.append(run_one("prev_winner_overrides @ 10m r=0.52%",
                           "10m", PREV_WINNER_OVERRIDES, PREV_WINNER_RISK))
    # Pure v3 defaults
    results.append(run_one("v3_defaults @ 7m r=0.52%",
                           "7m", {}, PREV_WINNER_RISK))
    results.append(run_one("v3_defaults @ 10m r=0.52%",
                           "10m", {}, PREV_WINNER_RISK))

    print()
    print("=" * 100)
    print("Hour analysis on the prev_winner_overrides @ 7m baseline")
    print("=" * 100)
    base = results[0]
    by_hour = bucket_by_hour(base["trades_raw"])
    print_hour_table(by_hour)
    print()
    by_dow = bucket_by_dow(base["trades_raw"])
    print_dow_table(by_dow)
