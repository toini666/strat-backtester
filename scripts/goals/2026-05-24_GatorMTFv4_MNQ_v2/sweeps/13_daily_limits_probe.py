"""Phase 13 (probe) — daily_limits intra_bar mode at the v2 winner config.

User constraint for v2 was daily_limits OFF (same as v1). The advisor flagged
this and CLAUDE.md recommends 'try intra_bar first'. This is the only
unexplored axis left. If it materially shifts the PnL/DD ratio, the user
has a real alternative — they can relax the constraint.

Sweep: daily_loss_limit ∈ {300, 400, 500, 700, 1000} × daily_win_limit ∈
{300, 500, 700, 1000, off} at the v2 winner config, intra_bar mode.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.goals._shared.harness import run_backtest, summarize, fmt_summary
from scripts.goals._shared.engine_settings import ui_default_engine_settings
from sweeps._campaign import (
    V1_WINNER_PARAMS, AUTO_CLOSE,
    START, END, SYMBOL, INTERVAL, STRATEGY,
    INITIAL_EQUITY, MAX_CONTRACTS,
    GOAL_DD, GOAL_PNL,
)

WINNER = {
    "amp_mult": 1.5, "hma1_len": 13, "hma2_len": 21,
    "case_a_on": True, "case_b_on": True,
    "case_c_on": False, "case_d_on": True,
    "final_rr": 1.5, "cooldown_bars": 90,
    "sl_lookback": 15, "tick_buffer": 6,
    "ssl_len": 20, "ssl_mult": 0.20,
    "sig_extreme_threshold": 33.0,
    "one_trade_per_window": True,
}


def _es_with_limits(loss=None, win=None, mode="intra_bar"):
    es = ui_default_engine_settings(STRATEGY)
    for w in es.blackout_windows:
        w.active = False
    es.auto_close_hour, es.auto_close_minute = AUTO_CLOSE
    if loss is not None:
        es.daily_loss_limit_enabled = True
        es.daily_loss_limit = float(loss)
    else:
        es.daily_loss_limit_enabled = False
    if win is not None:
        es.daily_win_limit_enabled = True
        es.daily_win_limit = float(win)
    else:
        es.daily_win_limit_enabled = False
    es.daily_limit_mode = mode
    return es


def _run(params, risk, es, label):
    t0 = time.time()
    r = run_backtest(
        strategy_name=STRATEGY,
        symbol=SYMBOL, interval=INTERVAL,
        start=START, end=END,
        strategy_params=params,
        initial_equity=INITIAL_EQUITY,
        risk_per_trade=risk,
        max_contracts=MAX_CONTRACTS,
        engine_settings=es,
    )
    s = summarize(r)
    s["elapsed_s"] = round(time.time() - t0, 1)
    print(f"  {label:<45s} {fmt_summary(s)}  ({s['elapsed_s']}s)")
    return s


def main():
    print("=" * 100)
    print("PHASE 13 — daily_limits intra_bar probe (user constraint was OFF; testing it)")
    print("=" * 100)
    SEED = dict(V1_WINNER_PARAMS)
    SEED.update(WINNER)

    # Baseline (no limits) at v2 winner risk for reference
    print()
    print("--- Reference (no limits) ---")
    _run(SEED, 0.28 / 100, _es_with_limits(None, None), "BASE risk=0.28% no limits")

    # ---- (A) loss-only intra_bar at risk 0.28% ----
    print()
    print("--- (A) loss-only intra_bar at risk=0.28% ---")
    for loss in [300, 400, 500, 700, 1000, 1500]:
        es = _es_with_limits(loss=loss, win=None, mode="intra_bar")
        _run(SEED, 0.28 / 100, es, f"loss={loss} intra_bar")

    # ---- (B) loss + win intra_bar at risk 0.28% ----
    print()
    print("--- (B) loss + win intra_bar at risk=0.28% ---")
    for loss, win in [(500, 500), (500, 700), (700, 500), (700, 1000), (1000, 1000)]:
        es = _es_with_limits(loss=loss, win=win, mode="intra_bar")
        _run(SEED, 0.28 / 100, es, f"loss={loss}/win={win} intra_bar")

    # ---- (C) loss intra_bar at higher risk (chase PnL goal) ----
    print()
    print("--- (C) loss-only intra_bar — higher risk levels ---")
    for risk in [0.40, 0.60, 0.80, 1.00]:
        for loss in [300, 500, 700, 1000]:
            es = _es_with_limits(loss=loss, win=None, mode="intra_bar")
            _run(SEED, risk / 100, es, f"loss={loss} risk={risk:.2f}%")

    # ---- (D) after_close fallback (CLAUDE.md says try intra_bar FIRST, fall back if needed) ----
    print()
    print("--- (D) after_close mode comparison at risk=0.28% ---")
    for loss in [300, 500, 700]:
        es = _es_with_limits(loss=loss, win=None, mode="after_close")
        _run(SEED, 0.28 / 100, es, f"loss={loss} after_close")

    print()
    print("=" * 100)
    print(f"Goal: PnL ≥ ${GOAL_PNL:,.0f} AND DD ≤ ${GOAL_DD:,.0f}")
    print("=" * 100)


if __name__ == "__main__":
    main()
