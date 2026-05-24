"""Phase 6 — Combo lattice on the best surviving levers + risk crawl.

Survivors so far:
- rr_tp ∈ {1.25, 1.5}             (1.5 needs to clear WR thinner)
- sig_range_reject lvl=3          (+$1.1k PnL +0.7pp WR on rr=1.25)
- BO 14-15                        (+$622 PnL on rr=1.25)
- BO 11-12                        (-$2.5k PnL but -$200 DD on rr=1.25;
                                   -$2.1k PnL but -$351 DD on rr=1.5+sr=3)
- BO 00-01                        (small +/- WR boost)
- BO 10-11                        (-$2.2k on rr=1.5+sr=3 / -$0.2k DD)

Test:
1. All combos of these BOs + sig_reject + rr_tp.
2. Risk crawl on the highest-PnL survivor with DD ≤ $2,500.
"""

from __future__ import annotations

import sys
from itertools import product
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
    "14-15":     (14, 0, 15, 0),
    "11-12":     (11, 0, 12, 0),
    "00-01":     (0,  0, 1,  0),
    "10-11":     (10, 0, 11, 0),
    "01-02":     (1,  0, 2,  0),
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
    print(f"  {label:<70s} {fmt_summary(s)}{flag}")
    return s


def main():
    print(f"=== Phase 6 — Combo lattice + risk crawl ===\n")
    sr3 = {"sig_range_reject": True, "sig_level": 3}

    print("--- 6A: 2-window combos on rr=1.25 + sr=3 ---")
    bo_pairs = [
        (["14-15"],),
        (["11-12"],),
        (["00-01"],),
        (["10-11"],),
        (["01-02"],),
        (["14-15", "11-12"],),
        (["14-15", "00-01"],),
        (["14-15", "10-11"],),
        (["11-12", "00-01"],),
        (["11-12", "10-11"],),
        (["00-01", "01-02"],),
    ]
    for (keys,) in bo_pairs:
        label = "rr=1.25+sr=3 + BO " + "+".join(keys)
        _bench(label, rr_tp=1.25, bo_keys=keys, extra_params=sr3)
    print()

    print("--- 6B: 2-window combos on rr=1.5 + sr=3 ---")
    for (keys,) in bo_pairs:
        label = "rr=1.5+sr=3 + BO " + "+".join(keys)
        _bench(label, rr_tp=1.5, bo_keys=keys, extra_params=sr3)
    print()

    print("--- 6C: 3-window combos on rr=1.5 + sr=3 ---")
    bo_triples = [
        ["14-15", "11-12", "00-01"],
        ["14-15", "10-11", "00-01"],
        ["14-15", "11-12", "01-02"],
        ["11-12", "10-11", "00-01"],
        ["10-11", "11-12", "01-02"],
    ]
    for keys in bo_triples:
        label = "rr=1.5+sr=3 + BO " + "+".join(keys)
        _bench(label, rr_tp=1.5, bo_keys=keys, extra_params=sr3)
    print()

    print("--- 6D: 3-window combos on rr=1.25 + sr=3 ---")
    for keys in bo_triples:
        label = "rr=1.25+sr=3 + BO " + "+".join(keys)
        _bench(label, rr_tp=1.25, bo_keys=keys, extra_params=sr3)
    print()

    print("--- 6E: Risk crawl on best DD-headroom rr=1.5 candidate ---")
    # rr=1.5+sr=3+BO 11-12 had DD=$1,971 → ~$529 headroom (Phase 5)
    for risk in [0.00625, 0.0070, 0.0075, 0.0080, 0.0085, 0.009]:
        _bench(f"rr=1.5+sr=3 + BO 11-12 risk={risk*100:.3f}%",
               rr_tp=1.5, bo_keys=["11-12"],
               extra_params=sr3, risk=risk)
    print()

    print("--- 6F: Risk crawl on best DD-headroom rr=1.25 candidate ---")
    # rr=1.25+sr=3 + BO 11-12 likely has similar headroom — check
    for risk in [0.00625, 0.0070, 0.0075, 0.0080, 0.0090, 0.010]:
        _bench(f"rr=1.25+sr=3 + BO 11-12 risk={risk*100:.3f}%",
               rr_tp=1.25, bo_keys=["11-12"],
               extra_params=sr3, risk=risk)
    print()

    print("--- 6G: Risk crawl on rr=1.5+sr=3 + BO 10-11+11-12 ---")
    for risk in [0.00625, 0.0070, 0.0075, 0.0080, 0.0085, 0.009]:
        _bench(f"rr=1.5+sr=3 + BO 10-12 risk={risk*100:.3f}%",
               rr_tp=1.5, bo_keys=["10-11", "11-12"],
               extra_params=sr3, risk=risk)
    print()


if __name__ == "__main__":
    main()
