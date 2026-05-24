"""Phase 0 — baseline v4 seed on extended period + WR diagnostic.

Outputs:
- Replays the v4 winner preset on the extended period.
- Hour-of-day WR + PnL + count
- Day-of-week WR + PnL + count
- Status breakdown (TP / SL / BE / Auto-close)
- Distribution of |entry-SL| (risk-points) for losing vs winning trades.
"""

from __future__ import annotations

import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from scripts.goals._shared.harness import run_backtest, summarize, fmt_summary
from scripts.goals._shared.engine_settings import (
    ui_default_engine_settings,
    make_engine_settings,
)
from scripts.goals._shared.analysis import bucket_by_hour, bucket_by_dow
from sweeps._campaign import (
    SEED_PARAMS, SEED_RISK, SEED_BLACKOUTS, SEED_AUTO_CLOSE,
    START, END, SYMBOL, INTERVAL, STRATEGY, INITIAL_EQUITY, MAX_CONTRACTS,
)


def _seed_engine_settings():
    es = ui_default_engine_settings(STRATEGY)
    # Deactivate UI defaults — we'll use v4's BO list explicitly.
    for w in es.blackout_windows:
        w.active = False
    return make_engine_settings(
        STRATEGY,
        auto_close_hour=SEED_AUTO_CLOSE[0],
        auto_close_minute=SEED_AUTO_CLOSE[1],
        extra_active_windows=[
            {"start_hour": sh, "start_minute": sm, "end_hour": eh, "end_minute": em}
            for sh, sm, eh, em in SEED_BLACKOUTS
        ],
    )


def main():
    print(f"=== Phase 0 — baseline v4 seed on {START} → {END} ===\n")

    es = _seed_engine_settings()
    # Drop the UI default actives (we replace them).
    es.blackout_windows = [w for w in es.blackout_windows if w.active]

    r = run_backtest(
        strategy_name=STRATEGY,
        symbol=SYMBOL,
        interval=INTERVAL,
        start=START,
        end=END,
        strategy_params=SEED_PARAMS,
        initial_equity=INITIAL_EQUITY,
        risk_per_trade=SEED_RISK,
        max_contracts=MAX_CONTRACTS,
        engine_settings=es,
    )
    s = summarize(r)
    print("Seed v4 on extended period:")
    print("  " + fmt_summary(s))
    print()

    trades = [t for t in r["trades"] if not t.get("excluded", False)]

    # --- Status breakdown ---
    status_counts = defaultdict(int)
    status_pnl    = defaultdict(float)
    status_wins   = defaultdict(int)
    for t in trades:
        # Use last leg status as the "final" outcome
        last_status = t["legs"][-1]["status"] if t.get("legs") else t.get("status", "?")
        status_counts[last_status] += 1
        status_pnl[last_status] += t["pnl"]
        if t["pnl"] > 0:
            status_wins[last_status] += 1

    print("Status breakdown (last-leg status of each trade):")
    print(f"  {'status':<28} {'n':>5} {'wins':>5}  {'WR':>5}  {'total':>11}  {'avg':>8}")
    for st_ in sorted(status_counts, key=lambda k: -status_counts[k]):
        n = status_counts[st_]
        w = status_wins[st_]
        wr = w / n * 100 if n else 0
        pnl = status_pnl[st_]
        avg = pnl / n if n else 0
        print(f"  {st_:<28} {n:>5} {w:>5}  {wr:>4.1f}%  ${pnl:>9,.0f}  ${avg:>6,.0f}")
    print()

    # --- Hour buckets ---
    print("Hour-of-day buckets (entry hour, reference Brussels):")
    by_hour = bucket_by_hour(trades)
    print(f"  {'Hour':<5}{'n':>5}{'wins':>5}{'WR':>7}{'total':>11}{'avg':>8}")
    for h in sorted(by_hour):
        d = by_hour[h]
        wins = round(d["n"] * d["win_rate"] / 100)
        print(f"  H={h:02d} {d['n']:>5} {wins:>5} {d['win_rate']:>5.1f}% "
              f"${d['total']:>8,.0f} ${d['avg']:>5,.0f}")
    print()

    # --- DOW buckets ---
    print("Day-of-week buckets:")
    by_dow = bucket_by_dow(trades)
    names = {0: "Mon", 1: "Tue", 2: "Wed", 3: "Thu", 4: "Fri", 5: "Sat", 6: "Sun"}
    print(f"  {'Day':<5}{'n':>5}{'wins':>5}{'WR':>7}{'total':>11}{'avg':>8}")
    for d_ in sorted(by_dow):
        d = by_dow[d_]
        wins = round(d["n"] * d["win_rate"] / 100)
        print(f"  {names.get(d_, '?'):<5}{d['n']:>5} {wins:>5} {d['win_rate']:>5.1f}% "
              f"${d['total']:>8,.0f} ${d['avg']:>5,.0f}")
    print()

    # --- Risk-points distribution ---
    risk_pts = []
    for t in trades:
        entry = t.get("entry_price", float("nan"))
        sl = t.get("stop_loss", float("nan"))
        if entry == entry and sl == sl:
            risk_pts.append((abs(entry - sl), t["pnl"] > 0))
    risk_w = [r for r, w in risk_pts if w]
    risk_l = [r for r, w in risk_pts if not w]
    if risk_w and risk_l:
        rw = pd.Series(risk_w)
        rl = pd.Series(risk_l)
        print("Risk-points distribution (|entry - SL|):")
        print(f"  Winners  (n={len(rw):>4}): mean={rw.mean():.1f}  med={rw.median():.1f}  "
              f"p25={rw.quantile(0.25):.1f}  p75={rw.quantile(0.75):.1f}  max={rw.max():.1f}")
        print(f"  Losers   (n={len(rl):>4}): mean={rl.mean():.1f}  med={rl.median():.1f}  "
              f"p25={rl.quantile(0.25):.1f}  p75={rl.quantile(0.75):.1f}  max={rl.max():.1f}")
    print()


if __name__ == "__main__":
    main()
