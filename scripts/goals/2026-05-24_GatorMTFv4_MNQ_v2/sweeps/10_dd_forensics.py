"""Phase 10 — DD forensics: identify the (peak, trough) event that pins DD floor.

Across risks 0.18-0.28%, DD = $2,126 identically — meaning one event saturates
the DD with the minimum 1-contract sizing. If we can identify and blackout
just that trade/cluster, the DD floor drops and we can run higher risk.
"""

from __future__ import annotations

import sys
from pathlib import Path
from collections import defaultdict

import pandas as pd

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.goals._shared.harness import run_backtest, summarize, fmt_summary
from scripts.goals._shared.engine_settings import ui_default_engine_settings
from sweeps._campaign import (
    V1_WINNER_PARAMS, AUTO_CLOSE,
    START, END, SYMBOL, INTERVAL, STRATEGY,
    INITIAL_EQUITY, MAX_CONTRACTS,
)

WINNER_PARAMS = {
    "amp_mult": 1.5, "hma1_len": 13, "hma2_len": 21,
    "case_a_on": True, "case_b_on": True,
    "case_c_on": False, "case_d_on": True,
    "final_rr": 1.5, "cooldown_bars": 90,
    "sl_lookback": 15, "tick_buffer": 6,
    "ssl_len": 20, "ssl_mult": 0.20,
    "sig_extreme_threshold": 33.0,
}
WINNER_RISK = 0.28 / 100


def _es_no_blackouts():
    es = ui_default_engine_settings(STRATEGY)
    for w in es.blackout_windows:
        w.active = False
    es.auto_close_hour, es.auto_close_minute = AUTO_CLOSE
    return es


def main():
    print("=" * 100)
    print("PHASE 10 — DD floor forensics on the v2 winner")
    print("=" * 100)
    es = _es_no_blackouts()
    SEED = dict(V1_WINNER_PARAMS)
    SEED.update(WINNER_PARAMS)

    r = run_backtest(
        strategy_name=STRATEGY,
        symbol=SYMBOL, interval=INTERVAL,
        start=START, end=END,
        strategy_params=SEED,
        initial_equity=INITIAL_EQUITY,
        risk_per_trade=WINNER_RISK,
        max_contracts=MAX_CONTRACTS,
        engine_settings=es,
    )
    s = summarize(r)
    print(f"Winner: {fmt_summary(s)}")
    print()

    # ---- Find the worst (peak, trough) in $ ----
    trades = sorted([t for t in r["trades"] if not t.get("excluded", False)],
                    key=lambda t: pd.to_datetime(t["entry_time"]))
    cum = 0.0
    peak = 0.0
    peak_idx = -1
    worst_dd = 0.0
    worst_peak_idx = -1
    worst_trough_idx = -1
    for i, t in enumerate(trades):
        cum += t["pnl"]
        if cum > peak:
            peak = cum
            peak_idx = i
        dd = peak - cum
        if dd > worst_dd:
            worst_dd = dd
            worst_peak_idx = peak_idx
            worst_trough_idx = i

    print(f"Worst trade-based DD: ${worst_dd:,.2f}")
    print(f"  Peak at trade #{worst_peak_idx}: {trades[worst_peak_idx]['exit_time']} (cum after = ${sum(t['pnl'] for t in trades[:worst_peak_idx+1]):,.2f})")
    print(f"  Trough at trade #{worst_trough_idx}: {trades[worst_trough_idx]['exit_time']} (cum after = ${sum(t['pnl'] for t in trades[:worst_trough_idx+1]):,.2f})")
    print(f"  Span: {worst_trough_idx - worst_peak_idx} trades")
    print()

    # ---- List the trades inside the DD window ----
    print("Trades inside the worst-DD window:")
    print(f"{'#':>4} {'entry_time':<19} {'side':<5} {'pnl':>10} {'cum':>10}")
    cum_local = sum(t["pnl"] for t in trades[:worst_peak_idx + 1])
    for i in range(worst_peak_idx + 1, worst_trough_idx + 1):
        cum_local += trades[i]["pnl"]
        side = trades[i].get("side") or trades[i].get("direction") or "?"
        et = pd.to_datetime(trades[i]["entry_time"]).strftime("%Y-%m-%d %H:%M:%S")
        print(f"{i:>4} {et:<19} {side:<5} ${trades[i]['pnl']:>+8,.2f}  ${cum_local:>+8,.2f}")

    # ---- Distribution of biggest single losers ----
    print()
    print("Top 10 single-trade losers (any time):")
    losers = sorted(trades, key=lambda t: t["pnl"])[:10]
    for i, t in enumerate(losers):
        et = pd.to_datetime(t["entry_time"]).strftime("%Y-%m-%d %H:%M:%S")
        side = t.get("side") or t.get("direction") or "?"
        print(f"  {i+1}. {et}  {side}  ${t['pnl']:>+8,.2f}")

    # ---- Hour distribution of largest losses (top 50 losers) ----
    print()
    print("Hour-of-day of top 50 single-trade losers:")
    big_losers = sorted(trades, key=lambda t: t["pnl"])[:50]
    by_hr = defaultdict(int)
    by_hr_sum = defaultdict(float)
    for t in big_losers:
        h = pd.to_datetime(t["entry_time"]).hour
        by_hr[h] += 1
        by_hr_sum[h] += t["pnl"]
    for h in sorted(by_hr):
        print(f"  H{h:02d}: n={by_hr[h]:>3}  total=${by_hr_sum[h]:>+8,.0f}")

    # ---- Date of the worst single-day cluster ----
    print()
    print("Worst single-day losses (by total $):")
    by_date = defaultdict(float)
    by_date_n = defaultdict(int)
    for t in trades:
        d = pd.to_datetime(t["entry_time"]).date()
        by_date[d] += t["pnl"]
        by_date_n[d] += 1
    worst_days = sorted(by_date.items(), key=lambda x: x[1])[:10]
    for d, total in worst_days:
        print(f"  {d}  total=${total:>+8,.0f}  N={by_date_n[d]}")


if __name__ == "__main__":
    main()
