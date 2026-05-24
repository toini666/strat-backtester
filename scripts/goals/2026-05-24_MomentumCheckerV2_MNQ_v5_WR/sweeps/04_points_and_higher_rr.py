"""Phase 4 — Points weights + higher-rr_tp paths with quality filters.

Two goals:
1. Find point-weight changes that boost WR/PnL.
2. See if higher rr_tp (1.5, 1.75, 2.0, 2.25) can reach WR ≥ 50% with
   quality filters / blackouts — that path gives higher PnL per win.
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


ANCHOR = {"rr_tp": 1.25}
ANCHOR_RISK = SEED_RISK


def _engine():
    es = ui_default_engine_settings(STRATEGY)
    for w in es.blackout_windows:
        w.active = False
    es = make_engine_settings(
        STRATEGY,
        auto_close_hour=SEED_AUTO_CLOSE[0],
        auto_close_minute=SEED_AUTO_CLOSE[1],
        extra_active_windows=[
            {"start_hour": sh, "start_minute": sm, "end_hour": eh, "end_minute": em}
            for sh, sm, eh, em in SEED_BLACKOUTS
        ],
    )
    es.blackout_windows = [w for w in es.blackout_windows if w.active]
    return es


def _bench(label: str, params_override: dict, risk: float = ANCHOR_RISK,
           extra_anchor: dict = None):
    params = dict(SEED_PARAMS)
    params.update(ANCHOR)
    if extra_anchor:
        params.update(extra_anchor)
    params.update(params_override)
    r = run_backtest(
        strategy_name=STRATEGY, symbol=SYMBOL, interval=INTERVAL,
        start=START, end=END,
        strategy_params=params,
        initial_equity=INITIAL_EQUITY, risk_per_trade=risk,
        max_contracts=MAX_CONTRACTS, engine_settings=_engine(),
    )
    s = summarize(r)
    flag = " ⭐" if (s["win_rate"] >= GOAL_WR and s["max_dd_$"] <= GOAL_DD) else ""
    print(f"  {label:<56s} {fmt_summary(s)}{flag}")
    return s


def main():
    print(f"=== Phase 4 — Points weights + higher rr_tp paths ===\n")

    _bench("ANCHOR (rr_tp=1.25)", {})
    print()

    print("--- 4A: Each point weight bumped to 2 (more emphasis) ---")
    weight_keys = [
        "pts_hw_sens", "pts_hw_value", "pts_hw_extreme", "pts_sig_extreme",
        "pts_cloud", "pts_delta",
        "pts_ema_break", "pts_st", "pts_alligator", "pts_alli_offset",
        "pts_retest_lips", "pts_ut_bot", "pts_stc",
        "pts_hma_break", "pts_hma_slow",
    ]
    for k in weight_keys:
        _bench(f"{k}=2", {k: 2})
    print()

    print("--- 4B: Each point weight zeroed (drop this signal) ---")
    for k in weight_keys + ["pts_ema_align"]:
        _bench(f"{k}=0", {k: 0})
    print()

    print("--- 4C: Higher rr_tp + sig_range_reject lvl=3 ---")
    for rr in [1.5, 1.75, 2.0, 2.25, 2.5]:
        _bench(f"rr_tp={rr} + sig_range_reject=3",
               {"rr_tp": rr, "sig_range_reject": True, "sig_level": 3},
               extra_anchor={})  # override anchor's rr_tp=1.25
    print()

    print("--- 4D: rr_tp=2.0 with quality filter combos ---")
    # Try to find rr_tp=2.0 path to WR≥50
    for label, override in [
        ("rr=2.0 base",
         {"rr_tp": 2.0}),
        ("rr=2.0 + sig_range_reject=3",
         {"rr_tp": 2.0, "sig_range_reject": True, "sig_level": 3}),
        ("rr=2.0 + sig_range_reject=5",
         {"rr_tp": 2.0, "sig_range_reject": True, "sig_level": 5}),
        ("rr=2.0 + sig_range_reject=10",
         {"rr_tp": 2.0, "sig_range_reject": True, "sig_level": 10}),
        ("rr=2.0 + sig_extreme=20",
         {"rr_tp": 2.0, "sig_extreme": 20}),
        ("rr=2.0 + hw_extreme=15",
         {"rr_tp": 2.0, "hw_extreme": 15}),
        ("rr=2.0 + min_gap=11",
         {"rr_tp": 2.0, "min_gap": 11}),
    ]:
        _bench(label, override, extra_anchor={})
    print()

    print("--- 4E: rr_tp=1.5 with quality filter combos ---")
    for label, override in [
        ("rr=1.5 + sig_range_reject=3",
         {"rr_tp": 1.5, "sig_range_reject": True, "sig_level": 3}),
        ("rr=1.5 + sig_range_reject=5",
         {"rr_tp": 1.5, "sig_range_reject": True, "sig_level": 5}),
        ("rr=1.5 + sig_extreme=25",
         {"rr_tp": 1.5, "sig_extreme": 25}),
        ("rr=1.5 + hw_extreme=15",
         {"rr_tp": 1.5, "hw_extreme": 15}),
    ]:
        _bench(label, override, extra_anchor={})
    print()


if __name__ == "__main__":
    main()
