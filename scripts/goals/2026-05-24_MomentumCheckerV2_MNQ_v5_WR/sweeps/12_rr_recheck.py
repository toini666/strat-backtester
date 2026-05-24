"""Phase 12 — Re-check rr_tp at the final winner anchor.

Phase 1 picked rr_tp=1.5 against the SEED anchor (WR cliff at 50.2%).
The final anchor now has +1.7pp WR headroom from sl_lookback=10 + sig_level=2.
Re-test rr_tp ∈ {1.5..1.8} at the winner anchor to see if a higher rr_tp
clears WR≥50% with bigger PnL per win.

Also test on the extended period 2025-01-02 (vs current 2025-01-07).
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
    SEED_PARAMS, SEED_BLACKOUTS, SEED_AUTO_CLOSE,
    START, END, SYMBOL, INTERVAL, STRATEGY,
    INITIAL_EQUITY, MAX_CONTRACTS, GOAL_WR, GOAL_DD,
)


WINNER_BO_KEYS = ["11-12", "14-15"]
BO_CANDIDATES = {
    "14-15": (14, 0, 15, 0),
    "11-12": (11, 0, 12, 0),
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
            {"start_hour": sh, "start_minute": sm,
             "end_hour": eh, "end_minute": em}
            for sh, sm, eh, em in all_bo
        ],
    )
    es.blackout_windows = [w for w in es.blackout_windows if w.active]
    return es


def _bench(label, rr_tp, bo_keys, extra_params, risk, start=START, end=END):
    p = dict(SEED_PARAMS); p["rr_tp"] = rr_tp; p.update(extra_params)
    r = run_backtest(
        strategy_name=STRATEGY, symbol=SYMBOL, interval=INTERVAL,
        start=start, end=end,
        strategy_params=p,
        initial_equity=INITIAL_EQUITY, risk_per_trade=risk,
        max_contracts=MAX_CONTRACTS, engine_settings=_engine(bo_keys),
    )
    s = summarize(r)
    flag = " ⭐" if (s["win_rate"] >= GOAL_WR and s["max_dd_$"] <= GOAL_DD) else ""
    print(f"  {label:<76s} {fmt_summary(s)}{flag}")
    return s


def main():
    sr2 = {"sig_range_reject": True, "sig_level": 2,
           "sl_lookback": 10, "tick_buffer": 1}

    print(f"=== Phase 12 — rr_tp recheck on final anchor ===\n")

    print("--- 12A: rr_tp sweep at the winner anchor (risk=0.83%) ---")
    for rr in [1.45, 1.50, 1.55, 1.60, 1.65, 1.70, 1.75, 1.80]:
        _bench(f"rr_tp={rr} sig=2+sl_lb=10+tb=1+BO 11-12+14-15 risk=0.83%",
               rr, WINNER_BO_KEYS, sr2, 0.0083)
    print()

    print("--- 12B: rr_tp=1.6 + risk crawl ---")
    for risk in [0.0070, 0.0075, 0.0080, 0.00825, 0.0083, 0.0085]:
        _bench(f"rr_tp=1.6 risk={risk*100:.4f}%",
               1.6, WINNER_BO_KEYS, sr2, risk)
    print()

    print("--- 12C: rr_tp=1.65 + risk crawl ---")
    for risk in [0.0070, 0.0075, 0.0080, 0.00825, 0.0083, 0.0085]:
        _bench(f"rr_tp=1.65 risk={risk*100:.4f}%",
               1.65, WINNER_BO_KEYS, sr2, risk)
    print()

    print("--- 12D: Extended period 2025-01-02 (instead of 2025-01-07) ---")
    EXTENDED_START = "2025-01-02T00:00"
    _bench("WINNER 0.83% on 2025-01-02 start",
           1.5, WINNER_BO_KEYS, sr2, 0.0083, start=EXTENDED_START)
    _bench("WINNER 0.82% on 2025-01-02 start (safer)",
           1.5, WINNER_BO_KEYS, sr2, 0.0082, start=EXTENDED_START)
    print()


if __name__ == "__main__":
    main()
