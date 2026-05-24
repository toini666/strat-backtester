"""Phase 14 — Finalise tick_buffer=2 risk crawl + final WINNER lock.

rr=1.55+tb=2 at risk=0.83% has DD=$2,367 with $133 headroom. Push risk
to see how high we can go before the next DD cliff.
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
    SYMBOL, INTERVAL, STRATEGY, INITIAL_EQUITY, MAX_CONTRACTS,
    GOAL_WR, GOAL_DD, END,
)

EXTENDED_START = "2025-01-02T00:00"
BO_CANDIDATES = {"14-15": (14, 0, 15, 0), "11-12": (11, 0, 12, 0)}


def _engine():
    es = ui_default_engine_settings(STRATEGY)
    for w in es.blackout_windows:
        w.active = False
    all_bo = list(SEED_BLACKOUTS) + [BO_CANDIDATES["11-12"], BO_CANDIDATES["14-15"]]
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


def _bench(label, extra_params, risk):
    p = dict(SEED_PARAMS); p["rr_tp"] = 1.55; p.update(extra_params)
    r = run_backtest(
        strategy_name=STRATEGY, symbol=SYMBOL, interval=INTERVAL,
        start=EXTENDED_START, end=END,
        strategy_params=p,
        initial_equity=INITIAL_EQUITY, risk_per_trade=risk,
        max_contracts=MAX_CONTRACTS, engine_settings=_engine(),
    )
    s = summarize(r)
    flag = " ⭐" if (s["win_rate"] >= GOAL_WR and s["max_dd_$"] <= GOAL_DD) else ""
    print(f"  {label:<70s} {fmt_summary(s)}{flag}")
    return s


def main():
    sr2 = {"sig_range_reject": True, "sig_level": 2,
           "sl_lookback": 10, "tick_buffer": 2}

    print(f"=== Phase 14 — rr=1.55+tb=2 risk crawl ===\n")
    for risk in [0.0080, 0.0082, 0.0083, 0.0084, 0.0085, 0.0086, 0.0087, 0.0088]:
        _bench(f"rr=1.55+tb=2 risk={risk*100:.4f}%", sr2, risk)
    print()


if __name__ == "__main__":
    main()
