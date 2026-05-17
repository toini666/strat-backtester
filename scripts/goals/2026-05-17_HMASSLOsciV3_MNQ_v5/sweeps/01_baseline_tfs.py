"""01 — Baseline replay V4 winner + hour/DOW + DD-anatomy analysis.

Replays the V4 winner config (ema=11, BO 11+14, r=0.0036) — confirms it reproduces
$50,770 / $2,268. Then dumps trade-by-hour, trade-by-DOW, and the worst losing
trades to find tighter DD candidates.
"""

from __future__ import annotations

import sys
from collections import defaultdict
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _campaign as C  # noqa: E402

from scripts.goals._shared.harness import run_backtest, summarize, fmt_summary  # noqa: E402
from scripts.goals._shared.engine_settings import make_engine_settings  # noqa: E402
from scripts.goals._shared.analysis import (  # noqa: E402
    bucket_by_hour,
    bucket_by_dow,
    print_hour_table,
    print_dow_table,
)


def _compute_dd_series(trades):
    """Build cumulative equity, return (peak_eq, max_dd_$, worst_dd_window)."""
    sorted_tr = sorted(trades, key=lambda t: pd.to_datetime(t["entry_time"]))
    cum = 0.0
    peak = 0.0
    max_dd = 0.0
    in_dd_start = None
    worst = (None, None, 0.0)
    for t in sorted_tr:
        if t.get("excluded"):
            continue
        cum += t["pnl"]
        if cum > peak:
            peak = cum
            in_dd_start = None
        dd = peak - cum
        if dd > 0 and in_dd_start is None:
            in_dd_start = t["entry_time"]
        if dd > max_dd:
            max_dd = dd
            worst = (in_dd_start, t["exit_time"], dd)
    return peak, max_dd, worst


def _worst_losing_trades(trades, n=20):
    losers = [t for t in trades if not t.get("excluded") and t["pnl"] < 0]
    losers.sort(key=lambda t: t["pnl"])
    return losers[:n]


def main():
    print(f"=== 01 BASELINE REPLAY V4 WINNER — TF={C.TF} ===\n")

    es = make_engine_settings(
        C.STRATEGY,
        extra_active_windows=[C.window(s, e) for (s, e) in [(11, 12), (14, 15)]],
    )

    result = run_backtest(
        strategy_name=C.STRATEGY,
        symbol=C.SYMBOL,
        interval=C.TF,
        start=C.START,
        end=C.END,
        strategy_params=dict(C.V4_WINNER_PARAMS),
        initial_equity=C.INITIAL_EQUITY,
        risk_per_trade=C.DEFAULT_RISK,
        max_contracts=C.MAX_CONTRACTS,
        engine_settings=es,
    )
    s = summarize(result)
    print(f"BASELINE V4: {fmt_summary(s)}\n")
    print(f"Expected V4: PnL≈$50,770 / DD≈$2,268 / N≈1389 / WR≈46.1% / PF≈1.58\n")

    trades = result["trades"]
    active = [t for t in trades if not t.get("excluded")]
    print(f"Active trades: {len(active)}\n")

    print("--- Bucket by Hour (entry hour, Brussels) ---")
    by_h = bucket_by_hour(trades)
    print_hour_table(by_h)

    print("\n--- Bucket by Day-of-Week ---")
    by_d = bucket_by_dow(trades)
    print_dow_table(by_d)

    # Hour ranking
    print("\n--- Most toxic hours (negative total $) ---")
    rank = sorted(by_h.items(), key=lambda kv: kv[1]["total"])
    for h, d in rank[:8]:
        if d["total"] < 0:
            print(f"  H={h:02d}  n={d['n']:>3}  total=${d['total']:>9,.0f}  "
                  f"avg=${d['avg']:>7,.0f}  WR={d['win_rate']:>4.0f}%")

    # DD anatomy
    print("\n--- DD anatomy ---")
    peak, max_dd, worst = _compute_dd_series(trades)
    print(f"Peak equity (cum):       ${peak:>10,.2f}")
    print(f"Max DD (from anatomy):   ${max_dd:>10,.2f}")
    if worst[0]:
        print(f"Worst DD window:         {worst[0]} → {worst[1]} ({worst[2]:,.0f}$)")

    # Worst single-trade losses
    print("\n--- 20 worst single losing trades (drives DD) ---")
    losers = _worst_losing_trades(trades, 20)
    print(f"{'#':>3} {'entry_time':<22} {'exit_time':<22} {'PnL':>10} {'bars':>5} {'side':>5}")
    for i, t in enumerate(losers, 1):
        bars = t.get("bars_in_trade", "-")
        side = t.get("side", "-")
        print(f"{i:>3} {str(t['entry_time']):<22} {str(t['exit_time']):<22} "
              f"${t['pnl']:>9,.0f} {bars:>5} {side:>5}")

    # Loser-hour distribution
    print("\n--- Hour distribution of large losers (|PnL| > $300) ---")
    big_loss_by_h = defaultdict(int)
    for t in active:
        if t["pnl"] < -300:
            big_loss_by_h[pd.to_datetime(t["entry_time"]).hour] += 1
    for h in sorted(big_loss_by_h):
        print(f"  H={h:02d}  count={big_loss_by_h[h]}")

    return s


if __name__ == "__main__":
    main()
