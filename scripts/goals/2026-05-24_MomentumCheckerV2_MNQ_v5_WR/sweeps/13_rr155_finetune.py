"""Phase 13 — Final tune on rr_tp=1.55 (new leader from Phase 12).

rr_tp=1.55 at risk=0.83% on the winner anchor gave:
  PnL $68,670 / DD $2,474 / WR 52.6% / N=607 / PF 1.65

Need:
- Fine risk crawl (0.83% → 0.84% to find max safe risk).
- Test on extended period 2025-01-02 start.
- Final pick.
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
BO_KEYS = ["11-12", "14-15"]
BO_CANDIDATES = {"14-15": (14, 0, 15, 0), "11-12": (11, 0, 12, 0)}


def _engine():
    es = ui_default_engine_settings(STRATEGY)
    for w in es.blackout_windows:
        w.active = False
    all_bo = list(SEED_BLACKOUTS) + [BO_CANDIDATES[k] for k in BO_KEYS]
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


def _bench(label, rr_tp, extra_params, risk, start=EXTENDED_START):
    p = dict(SEED_PARAMS); p["rr_tp"] = rr_tp; p.update(extra_params)
    r = run_backtest(
        strategy_name=STRATEGY, symbol=SYMBOL, interval=INTERVAL,
        start=start, end=END,
        strategy_params=p,
        initial_equity=INITIAL_EQUITY, risk_per_trade=risk,
        max_contracts=MAX_CONTRACTS, engine_settings=_engine(),
    )
    s = summarize(r)
    flag = " ⭐" if (s["win_rate"] >= GOAL_WR and s["max_dd_$"] <= GOAL_DD) else ""
    print(f"  {label:<76s} {fmt_summary(s)}{flag}")
    return s


def main():
    sr2 = {"sig_range_reject": True, "sig_level": 2,
           "sl_lookback": 10, "tick_buffer": 1}

    print(f"=== Phase 13 — rr_tp=1.55 final tune (extended start 2025-01-02) ===\n")

    print("--- 13A: Fine risk crawl on rr_tp=1.55 ---")
    for risk in [0.0075, 0.0080, 0.0082, 0.0083, 0.0084, 0.0085, 0.0086,
                 0.0087, 0.0088, 0.0090]:
        _bench(f"rr_tp=1.55 risk={risk*100:.4f}%", 1.55, sr2, risk)
    print()

    print("--- 13B: Side-by-side final candidates ---")
    candidates = [
        ("rr=1.50 risk=0.83% (Phase 11 winner)", 1.50, 0.0083),
        ("rr=1.55 risk=0.83%", 1.55, 0.0083),
        ("rr=1.55 risk=0.84%", 1.55, 0.0084),
        ("rr=1.55 risk=0.85%", 1.55, 0.0085),
        ("rr=1.55 risk=0.82%", 1.55, 0.0082),
    ]
    for label, rr, risk in candidates:
        _bench(label, rr, sr2, risk)
    print()

    # Also test without tick_buffer for rr=1.55
    print("--- 13C: rr=1.55 + tick_buffer={0,2} sweep ---")
    for tb in [0, 1, 2]:
        p = dict(sr2); p["tick_buffer"] = tb
        _bench(f"rr=1.55 tb={tb} risk=0.83%", 1.55, p, 0.0083)
    print()


if __name__ == "__main__":
    main()
