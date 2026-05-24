"""Phase 0 — Baseline reproduction on extended period + hour/DOW WR diagnostic.

1. Replay seed on seed-period to cross-check vs preset metrics (PnL $60,474 / DD $2,182 / WR 39.6 %).
2. Replay seed on extended period (2025-01-02 -> 2026-05-22) -> our true anchor.
3. Hour-of-day WR buckets to find low-WR clusters for Phase 4 blackouts.
4. Day-of-week WR buckets.

Math anchor:
  At rr_tp=3, break-even WR = 25 %. Seed observed = 39.6 %. Edge = +14.6 pp.
  Expected WR at rr_tp=X = 1/(1+X) + 14.6 pp.
"""
from __future__ import annotations
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.goals._shared.harness import run_backtest, summarize, fmt_summary
from scripts.goals._shared.analysis import bucket_by_hour, bucket_by_dow
from _campaign import (
    SEED_PARAMS, SEED_RISK_PCT, build_seed_engine_settings,
    STRATEGY, SYMBOL, INTERVAL, INITIAL_EQUITY, MAX_CONTRACTS,
    START, END, SEED_PERIOD_START, SEED_PERIOD_END,
)


def run_label(label, **kwargs):
    r = run_backtest(**kwargs)
    s = summarize(r)
    s["label"] = label
    print(f"{label:<48s} {fmt_summary(s)}")
    return r, s


def main():
    # 1) Seed-period replay (sanity vs preset)
    r0, s0 = run_label(
        "0a seed @ seed-period",
        strategy_name=STRATEGY, symbol=SYMBOL, interval=INTERVAL,
        start=SEED_PERIOD_START, end=SEED_PERIOD_END,
        initial_equity=INITIAL_EQUITY, risk_per_trade=SEED_RISK_PCT,
        max_contracts=MAX_CONTRACTS,
        strategy_params=SEED_PARAMS,
        engine_settings=build_seed_engine_settings(),
    )

    # 2) Extended-period replay -> TRUE ANCHOR for the campaign
    r1, s1 = run_label(
        "0b seed @ extended-period",
        strategy_name=STRATEGY, symbol=SYMBOL, interval=INTERVAL,
        start=START, end=END,
        initial_equity=INITIAL_EQUITY, risk_per_trade=SEED_RISK_PCT,
        max_contracts=MAX_CONTRACTS,
        strategy_params=SEED_PARAMS,
        engine_settings=build_seed_engine_settings(),
    )

    # 3) Hour-of-day WR diagnostic on extended period (true anchor)
    print("\n--- HOUR-OF-DAY WR BUCKETS (extended period) ---")
    h_buckets = bucket_by_hour(r1["trades"])
    print(f"{'H':>3}  {'N':>4}  {'WR%':>6}  {'AvgPnL':>9}  {'Total':>10}")
    for h in sorted(h_buckets):
        b = h_buckets[h]
        print(f"{h:>3}  {b['n']:>4}  {b['win_rate']:>6.1f}  {b['avg']:>9.2f}  {b['total']:>10.2f}")

    # 4) Day-of-week diagnostic
    print("\n--- DAY-OF-WEEK WR BUCKETS (Mon=0..Sun=6) ---")
    d_buckets = bucket_by_dow(r1["trades"])
    print(f"{'D':>3}  {'N':>4}  {'WR%':>6}  {'AvgPnL':>9}  {'Total':>10}")
    for d in sorted(d_buckets):
        b = d_buckets[d]
        print(f"{d:>3}  {b['n']:>4}  {b['win_rate']:>6.1f}  {b['avg']:>9.2f}  {b['total']:>10.2f}")


if __name__ == "__main__":
    main()
