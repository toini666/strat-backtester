"""Phase 8 — Deep dive on sl_lookback (Phase 7 surprise winner).

sl_lookback=10 on rr=1.5+sr=3 gave $49,525 / $2,357 / WR 51.6% / PF 1.54
— a HUGE jump from sl_lookback=5 (seed). Need to understand:
- Is the optimum at 10, 8, 12, 15?
- Does it stack with BO 11-12 / tick_buffer / risk?
- Does the lookback finding apply to rr=1.25 path?
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
    print(f"  {label:<76s} {fmt_summary(s)}{flag}")
    return s


def main():
    sr3 = {"sig_range_reject": True, "sig_level": 3}

    print("=== Phase 8 — sl_lookback deep dive ===\n")

    print("--- 8A: sl_lookback sweep on rr=1.5+sr=3 ---")
    for lb in [3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 15, 18, 20]:
        p = dict(sr3); p["sl_lookback"] = lb
        _bench(f"rr=1.5+sr=3 sl_lookback={lb}", rr_tp=1.5, bo_keys=[], extra_params=p)
    print()

    print("--- 8B: sl_lookback sweep on rr=1.25+sr=3 ---")
    for lb in [3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 15]:
        p = dict(sr3); p["sl_lookback"] = lb
        _bench(f"rr=1.25+sr=3 sl_lookback={lb}", rr_tp=1.25, bo_keys=[], extra_params=p)
    print()

    print("--- 8C: sl_lookback sweep on rr=2.0+sr=3 (does it unlock WR≥50?) ---")
    for lb in [5, 8, 10, 12, 15, 20]:
        p = dict(sr3); p["sl_lookback"] = lb
        _bench(f"rr=2.0+sr=3 sl_lookback={lb}", rr_tp=2.0, bo_keys=[], extra_params=p)
    print()

    print("--- 8D: sl_lookback=10 + BO 11-12 + risk crawl ---")
    p = dict(sr3); p["sl_lookback"] = 10
    for risk in [0.00625, 0.0065, 0.00675, 0.0070, 0.00725, 0.0075]:
        _bench(f"rr=1.5+sr=3+sl_lb=10 + BO 11-12 risk={risk*100:.3f}%",
               rr_tp=1.5, bo_keys=["11-12"], extra_params=p, risk=risk)
    print()

    print("--- 8E: sl_lookback=10 + risk crawl (no BO) ---")
    p = dict(sr3); p["sl_lookback"] = 10
    for risk in [0.00625, 0.0065, 0.00675, 0.0070, 0.00725, 0.0075]:
        _bench(f"rr=1.5+sr=3+sl_lb=10 risk={risk*100:.3f}%",
               rr_tp=1.5, bo_keys=[], extra_params=p, risk=risk)
    print()

    print("--- 8F: sl_lookback=10 + BO 10-12 + risk crawl ---")
    p = dict(sr3); p["sl_lookback"] = 10
    for risk in [0.00625, 0.0065, 0.00675, 0.0070, 0.00725, 0.0075]:
        _bench(f"rr=1.5+sr=3+sl_lb=10 + BO 10-12 risk={risk*100:.3f}%",
               rr_tp=1.5, bo_keys=["10-12"], extra_params=p, risk=risk)
    print()

    print("--- 8G: sl_lookback=10 + tick_buffer combos ---")
    for tb in [0, 1, 2, 3]:
        p = dict(sr3); p["sl_lookback"] = 10; p["tick_buffer"] = tb
        _bench(f"rr=1.5+sr=3+sl_lb=10 tick_buffer={tb}",
               rr_tp=1.5, bo_keys=[], extra_params=p)
    print()


if __name__ == "__main__":
    main()
