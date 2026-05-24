"""Phase 10 — Crystallize the winner.

Top candidates from Phase 9:
- A. sl_lb=10+tb=1 + BO 11-12 risk=0.80%               → $62,142 / $2,435 / WR 51.8% / PF 1.55
- B. sl_lb=10    + BO 11-12+14-15 risk=0.80%           → $61,080 / $2,429 / WR 52.5% / PF 1.59
- C. sl_lb=10    + BO 14-15 risk=0.65%                 → $50,352 / $2,236 / WR 52.3% / PF 1.58
- D. sl_lb=9     + BO 11-12 risk=0.80%                 → $61,237 / $2,429 / WR 51.5% / PF 1.53

Phase 10:
- Combine B + tb=1 → triple combo
- Push risk on B & D fine
- Validate sig_level=2 vs 3
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
    print(f"  {label:<86s} {fmt_summary(s)}{flag}")
    return s


def main():
    sr3 = {"sig_range_reject": True, "sig_level": 3}

    print("=== Phase 10 — Final crystallization ===\n")

    print("--- 10A: TRIPLE combo: sl_lb=10+tb=1+BO 11-12+14-15 risk crawl ---")
    p = dict(sr3); p["sl_lookback"] = 10; p["tick_buffer"] = 1
    for risk in [0.0070, 0.00725, 0.0075, 0.00775, 0.0080, 0.00825, 0.0085]:
        _bench(f"sl_lb=10+tb=1+BO 11-12+14-15 risk={risk*100:.4f}%",
               rr_tp=1.5, bo_keys=["11-12", "14-15"], extra_params=p, risk=risk)
    print()

    print("--- 10B: sl_lb=10+tb=1+BO 11-12 fine risk above 0.80% ---")
    p = dict(sr3); p["sl_lookback"] = 10; p["tick_buffer"] = 1
    for risk in [0.0080, 0.00815, 0.00825, 0.0083, 0.00835, 0.0084, 0.0085]:
        _bench(f"sl_lb=10+tb=1+BO 11-12 risk={risk*100:.4f}%",
               rr_tp=1.5, bo_keys=["11-12"], extra_params=p, risk=risk)
    print()

    print("--- 10C: sig_level sweep on the best (sl_lb=10+BO 11-12+14-15 risk=0.80%) ---")
    for sl in [0, 2, 3, 4, 5, 7]:
        p = {"sig_range_reject": (sl > 0), "sig_level": sl, "sl_lookback": 10}
        _bench(f"sig_level={sl} sl_lb=10+BO 11-12+14-15 risk=0.80%",
               rr_tp=1.5, bo_keys=["11-12", "14-15"], extra_params=p, risk=0.0080)
    print()

    print("--- 10D: sl_lookback={9,10,11} with the best BO+risk combo ---")
    for lb in [8, 9, 10, 11, 12]:
        p = dict(sr3); p["sl_lookback"] = lb; p["tick_buffer"] = 1
        _bench(f"sl_lb={lb}+tb=1+BO 11-12+14-15 risk=0.80%",
               rr_tp=1.5, bo_keys=["11-12", "14-15"], extra_params=p, risk=0.0080)
    print()

    print("--- 10E: Verify TRIPLE candidate at very fine risk ---")
    # Best from 10A — replicate at neighbouring risks
    p = dict(sr3); p["sl_lookback"] = 10; p["tick_buffer"] = 1
    for risk in [0.00765, 0.0078, 0.0079, 0.0080, 0.0081, 0.00815, 0.0082]:
        _bench(f"sl_lb=10+tb=1+BO 11-12+14-15 risk={risk*100:.4f}%",
               rr_tp=1.5, bo_keys=["11-12", "14-15"], extra_params=p, risk=risk)
    print()


if __name__ == "__main__":
    main()
