"""Phase 5 — Blackout windows on the rr_tp=1.25 anchor + run diagnostic
hour buckets on the rr_tp=2.0 path to see if blackouts unlock WR≥50.

From Phase 0 diagnostic on seed (rr_tp=2.5):
- LOW WR clusters: H=01 (28%), H=10 (36%, 59n), H=11 (37%, 40n),
  H=14 (34%, 65n), H=15 (36%, 104n), H=00 (36%, 64n), H=23 (25%)
- HIGH WR clusters: H=06 (68%), H=08 (53%), H=09 (56%), H=16 (54%)

Test:
- Each candidate window in isolation, anchored on rr=1.25 AND rr=2.0
  (to see if BO unlocks the higher-PnL path).
- Then re-diagnose hour buckets at rr_tp=2.0 to find what's really losing
  at that rr_tp.
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
    ui_default_engine_settings, make_engine_settings,
)
from scripts.goals._shared.analysis import bucket_by_hour
from sweeps._campaign import (
    SEED_PARAMS, SEED_RISK, SEED_BLACKOUTS, SEED_AUTO_CLOSE,
    START, END, SYMBOL, INTERVAL, STRATEGY, INITIAL_EQUITY, MAX_CONTRACTS,
    GOAL_WR, GOAL_DD,
)


def _engine(extra_blackouts: list = None):
    """Build engine settings with seed BOs + optional extras."""
    es = ui_default_engine_settings(STRATEGY)
    for w in es.blackout_windows:
        w.active = False
    all_bo = list(SEED_BLACKOUTS) + list(extra_blackouts or [])
    es = make_engine_settings(
        STRATEGY,
        auto_close_hour=SEED_AUTO_CLOSE[0],
        auto_close_minute=SEED_AUTO_CLOSE[1],
        extra_active_windows=[
            {"start_hour": sh, "start_minute": sm, "end_hour": eh, "end_minute": em}
            for sh, sm, eh, em in all_bo
        ],
    )
    es.blackout_windows = [w for w in es.blackout_windows if w.active]
    return es


def _bench(label: str, rr_tp: float, extra_blackouts: list = None,
           extra_params: dict = None, risk: float = SEED_RISK):
    params = dict(SEED_PARAMS)
    params["rr_tp"] = rr_tp
    if extra_params:
        params.update(extra_params)
    r = run_backtest(
        strategy_name=STRATEGY, symbol=SYMBOL, interval=INTERVAL,
        start=START, end=END,
        strategy_params=params,
        initial_equity=INITIAL_EQUITY, risk_per_trade=risk,
        max_contracts=MAX_CONTRACTS,
        engine_settings=_engine(extra_blackouts),
    )
    s = summarize(r)
    flag = " ⭐" if (s["win_rate"] >= GOAL_WR and s["max_dd_$"] <= GOAL_DD) else ""
    print(f"  {label:<60s} {fmt_summary(s)}{flag}")
    return s, r


def main():
    print(f"=== Phase 5 — Blackout windows ===\n")

    # First: diagnose hour buckets at rr_tp=2.0 to see what's losing
    print("--- 5A: Hour bucket diagnostic at rr_tp=2.0 (no extra BO) ---")
    s, r = _bench("rr=2.0 base", rr_tp=2.0)
    trades = [t for t in r["trades"] if not t.get("excluded", False)]
    by_hour = bucket_by_hour(trades)
    print(f"  {'Hour':<5}{'n':>5}{'wins':>5}{'WR':>7}{'total':>11}{'avg':>8}")
    for h in sorted(by_hour):
        d = by_hour[h]
        wins = round(d["n"] * d["win_rate"] / 100)
        print(f"  H={h:02d} {d['n']:>5} {wins:>5} {d['win_rate']:>5.1f}% "
              f"${d['total']:>8,.0f} ${d['avg']:>5,.0f}")
    print()

    # Phase 5B — BO sweep on rr=1.25 anchor
    print("--- 5B: Single-window BO on rr_tp=1.25 anchor ---")
    candidates_bo = [
        # Low-WR clusters from Phase 0
        ((0, 0, 1, 0),    "BO 00-01"),
        ((1, 0, 2, 0),    "BO 01-02"),
        ((0, 0, 2, 0),    "BO 00-02"),
        ((10, 0, 11, 0),  "BO 10-11"),
        ((11, 0, 12, 0),  "BO 11-12"),
        ((10, 0, 12, 0),  "BO 10-12"),
        ((14, 0, 15, 30), "BO 14-15:30"),
        ((14, 0, 15, 0),  "BO 14-15"),
        ((15, 30, 17, 0), "BO 15:30-17"),
        ((23, 0, 23, 59), "BO 23:00-23:59"),
    ]
    for (sh, sm, eh, em), label in candidates_bo:
        _bench(f"rr=1.25 + {label}", rr_tp=1.25,
               extra_blackouts=[(sh, sm, eh, em)])
    print()

    # Phase 5C — BO sweep on rr_tp=1.5 + sig_range_reject=3 anchor (Phase 4 winner)
    print("--- 5C: Single-window BO on rr=1.5 + sig_reject=3 anchor ---")
    extra = {"sig_range_reject": True, "sig_level": 3}
    for (sh, sm, eh, em), label in candidates_bo:
        _bench(f"rr=1.5+sr=3 + {label}", rr_tp=1.5,
               extra_blackouts=[(sh, sm, eh, em)],
               extra_params=extra)
    print()

    # Phase 5D — BO sweep on rr_tp=2.0 + sig_range_reject=3 (try to unlock WR≥50)
    print("--- 5D: Single-window BO on rr=2.0 + sig_reject=3 (push WR over 50) ---")
    for (sh, sm, eh, em), label in candidates_bo:
        _bench(f"rr=2.0+sr=3 + {label}", rr_tp=2.0,
               extra_blackouts=[(sh, sm, eh, em)],
               extra_params=extra)
    print()


if __name__ == "__main__":
    main()
