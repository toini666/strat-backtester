"""Phase 11 — Final winner selection.

Best contenders after Phase 10:
- sig_lvl=2 + sl_lb=10+tb=0+BO 11-12+14-15 risk=0.80% → $64,606 / $2,364 / WR 52.9% / PF 1.62
- sig_lvl=3 + sl_lb=10+tb=1+BO 11-12+14-15 risk=0.815% → $61,878 / $2,435 / WR 52.6% / PF 1.60
- sig_lvl=3 + sl_lb=10+tb=1+BO 11-12 risk=0.8150% → $62,717 / $2,435 / WR 51.8% / PF 1.55

Phase 11:
- Fine risk crawl on sig_lvl=2 (the new leader)
- Try sig_lvl=2 + tick_buffer=1
- Final WINNER selection
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
    print(f"  {label:<88s} {fmt_summary(s)}{flag}")
    return s


def main():
    print(f"=== Phase 11 — Final winner selection ===\n")

    print("--- 11A: sig_level=2 + sl_lb=10 + BO 11-12+14-15 risk crawl ---")
    for risk in [0.0070, 0.00725, 0.0075, 0.00775, 0.0080, 0.00815, 0.0082,
                 0.00825, 0.0083, 0.0085]:
        p = {"sig_range_reject": True, "sig_level": 2, "sl_lookback": 10}
        _bench(f"sig=2+sl_lb=10+BO 11-12+14-15 risk={risk*100:.4f}%",
               rr_tp=1.5, bo_keys=["11-12", "14-15"], extra_params=p, risk=risk)
    print()

    print("--- 11B: sig=2 + sl_lb=10 + tb=1 + BO 11-12+14-15 ---")
    for risk in [0.00775, 0.0080, 0.00815, 0.0082, 0.0083, 0.0084, 0.0085]:
        p = {"sig_range_reject": True, "sig_level": 2,
             "sl_lookback": 10, "tick_buffer": 1}
        _bench(f"sig=2+sl_lb=10+tb=1+BO 11-12+14-15 risk={risk*100:.4f}%",
               rr_tp=1.5, bo_keys=["11-12", "14-15"], extra_params=p, risk=risk)
    print()

    print("--- 11C: sig=2 + sl_lb=10 + BO 11-12 (no 14-15) risk crawl ---")
    for risk in [0.0075, 0.0080, 0.00815, 0.0082, 0.0083, 0.0085]:
        p = {"sig_range_reject": True, "sig_level": 2, "sl_lookback": 10}
        _bench(f"sig=2+sl_lb=10+BO 11-12 risk={risk*100:.4f}%",
               rr_tp=1.5, bo_keys=["11-12"], extra_params=p, risk=risk)
    print()

    print("--- 11D: sig=0 (no reject) + sl_lb=10 + BO 11-12+14-15 risk crawl ---")
    # sig=0 already showed $65,797 at 0.80% but DD over by $37; try lower risks
    for risk in [0.0075, 0.0076, 0.0077, 0.0078, 0.0079, 0.0080]:
        p = {"sig_range_reject": False, "sl_lookback": 10}
        _bench(f"sig=0+sl_lb=10+BO 11-12+14-15 risk={risk*100:.4f}%",
               rr_tp=1.5, bo_keys=["11-12", "14-15"], extra_params=p, risk=risk)
    print()

    print("--- 11E: WINNER candidates side-by-side ---")
    candidates = [
        # (label, rr, bo_keys, params, risk)
        ("A: sig=2 sl_lb=10 tb=0 BO 11-12+14-15", 1.5, ["11-12", "14-15"],
         {"sig_range_reject": True, "sig_level": 2, "sl_lookback": 10}, 0.0080),
        ("B: sig=3 sl_lb=10 tb=1 BO 11-12+14-15", 1.5, ["11-12", "14-15"],
         {"sig_range_reject": True, "sig_level": 3, "sl_lookback": 10,
          "tick_buffer": 1}, 0.00815),
        ("C: sig=3 sl_lb=10 tb=1 BO 11-12",       1.5, ["11-12"],
         {"sig_range_reject": True, "sig_level": 3, "sl_lookback": 10,
          "tick_buffer": 1}, 0.00815),
    ]
    for label, rr, bo, params, risk in candidates:
        _bench(label, rr_tp=rr, bo_keys=bo, extra_params=params, risk=risk)
    print()


if __name__ == "__main__":
    main()
