"""Phase 9 — Pareto edge crawl on the winners from Phase 8.

Top contenders:
A. rr=1.5+sr=3+sl_lb=10 + BO 11-12 risk=0.750%  → $59,706 / $2,455 / 51.8%
B. rr=1.5+sr=3+sl_lb=10              risk=0.650% → $50,817 / $2,384 / 51.6%
C. rr=1.5+sr=3+sl_lb=9 + BO 11-12               → ?  (LB=9 alone had DD=$1,996)
D. rr=1.5+sr=3+sl_lb=13                          → $48,900 / $2,425 / 51.8%

Goal:
- Crawl risk at 0.005% granularity around the DD=$2,500 edge.
- Try sl_lb=9 + BO 11-12 + tick_buffer=1.
- Test adding a second BO to lower DD further (more risk headroom).
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.goals._shared.harness import run_backtest, summarize, fmt_summary
from scripts.goals._shared.engine_settings import (
    ui_default_engine_settings, make_engine_settings,
)
from sweeps._campaign import (
    SEED_PARAMS, SEED_RISK, SEED_BLACKOUTS, SEED_AUTO_CLOSE,
    START, END, SYMBOL, INTERVAL, STRATEGY, INITIAL_EQUITY, MAX_CONTRACTS,
    GOAL_WR, GOAL_DD,
)


BO_CANDIDATES = {
    "14-15": (14, 0, 15, 0),
    "11-12": (11, 0, 12, 0),
    "00-01": (0,  0, 1,  0),
    "10-11": (10, 0, 11, 0),
    "10-12": (10, 0, 12, 0),
    "01-02": (1,  0, 2,  0),
}


def _engine(extra_blackout_keys: list = None):
    es = ui_default_engine_settings(STRATEGY)
    for w in es.blackout_windows:
        w.active = False
    all_bo = list(SEED_BLACKOUTS)
    for k in (extra_blackout_keys or []):
        all_bo.append(BO_CANDIDATES[k])
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


def _bench(label: str, rr_tp: float, bo_keys: list,
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
        engine_settings=_engine(bo_keys),
    )
    s = summarize(r)
    flag = " ⭐" if (s["win_rate"] >= GOAL_WR and s["max_dd_$"] <= GOAL_DD) else ""
    print(f"  {label:<82s} {fmt_summary(s)}{flag}")
    return s


def main():
    sr3 = {"sig_range_reject": True, "sig_level": 3}

    print("=== Phase 9 — Pareto edge crawl ===\n")

    print("--- 9A: Fine risk crawl on rr=1.5+sr=3+sl_lb=10 + BO 11-12 ---")
    p = dict(sr3); p["sl_lookback"] = 10
    for risk in [0.0070, 0.00715, 0.0072, 0.00725, 0.0073, 0.00735, 0.0074,
                 0.00745, 0.0075, 0.00755, 0.0076, 0.00765, 0.0077]:
        _bench(f"rr=1.5+sr=3+sl_lb=10+BO 11-12 risk={risk*100:.4f}%",
               rr_tp=1.5, bo_keys=["11-12"], extra_params=p, risk=risk)
    print()

    print("--- 9B: sl_lookback=9 + BO 11-12 + risk crawl ---")
    p = dict(sr3); p["sl_lookback"] = 9
    for risk in [0.00625, 0.0065, 0.00675, 0.0070, 0.00725, 0.0075, 0.0080]:
        _bench(f"rr=1.5+sr=3+sl_lb=9+BO 11-12 risk={risk*100:.4f}%",
               rr_tp=1.5, bo_keys=["11-12"], extra_params=p, risk=risk)
    print()

    print("--- 9C: sl_lb=10 + tick_buffer=1 + BO 11-12 + risk crawl ---")
    p = dict(sr3); p["sl_lookback"] = 10; p["tick_buffer"] = 1
    for risk in [0.0070, 0.00725, 0.0075, 0.00775, 0.0080]:
        _bench(f"rr=1.5+sr=3+sl_lb=10+tb=1+BO 11-12 risk={risk*100:.4f}%",
               rr_tp=1.5, bo_keys=["11-12"], extra_params=p, risk=risk)
    print()

    print("--- 9D: Adding a 2nd BO to BO 11-12 base (look for DD reduction) ---")
    p = dict(sr3); p["sl_lookback"] = 10
    for second_bo, label in [
        (["11-12", "00-01"], "BO 11-12+00-01"),
        (["11-12", "14-15"], "BO 11-12+14-15"),
        (["11-12", "01-02"], "BO 11-12+01-02"),
        (["11-12", "10-11"], "BO 10-12"),
    ]:
        # First at base risk
        _bench(f"rr=1.5+sr=3+sl_lb=10+{label} risk=0.625%",
               rr_tp=1.5, bo_keys=second_bo, extra_params=p, risk=0.00625)
    print()

    print("--- 9E: If DD shrinks, push risk higher on 2-BO combos ---")
    # We'll find the best DD-reducer in 9D then crawl risk on it
    for second_bo, label in [
        (["11-12", "00-01"], "BO 11-12+00-01"),
        (["11-12", "14-15"], "BO 11-12+14-15"),
    ]:
        for risk in [0.0070, 0.0075, 0.0080, 0.0085]:
            _bench(f"rr=1.5+sr=3+sl_lb=10+{label} risk={risk*100:.4f}%",
                   rr_tp=1.5, bo_keys=second_bo, extra_params=p, risk=risk)
        print()

    print("--- 9F: rr=1.5+sr=3+sl_lb=10 with single BO 14-15 (different than 11-12) ---")
    p = dict(sr3); p["sl_lookback"] = 10
    for risk in [0.00625, 0.0065, 0.00675, 0.0070, 0.00725, 0.0075]:
        _bench(f"rr=1.5+sr=3+sl_lb=10+BO 14-15 risk={risk*100:.4f}%",
               rr_tp=1.5, bo_keys=["14-15"], extra_params=p, risk=risk)
    print()


if __name__ == "__main__":
    main()
