"""Phase 1 — Structural WR levers (rr_tp + be_at_rr + risk).

WR is bounded mathematically by 1/(1+rr_tp) + edge. Seed rr_tp=2.5 gives a
break-even WR of 28.6% — currently at 41.3%, so ~13 pp of edge.

To reach 50% WR, the easiest mathematical path is to lower rr_tp. We sweep:
- rr_tp ∈ {1.0, 1.25, 1.5, 1.75, 2.0, 2.25, 2.5}
- be_at_rr ∈ {0.0, 0.5, 1.0, 1.5, 2.0}   (one-way: BE moves don't help WR
  directly but may reduce DD — useful when we trade PnL for WR)

Then a small risk sweep on the most promising rr_tp values to keep DD ≤ 2500.
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


def _bench(label: str, params_override: dict, risk: float = SEED_RISK):
    params = dict(SEED_PARAMS)
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
    print(f"  {label:<48s} {fmt_summary(s)}{flag}")
    return s


def main():
    print(f"=== Phase 1 — Structural WR levers (rr_tp / be_at_rr) ===\n")
    print(f"Goal: WR ≥ {GOAL_WR}% / DD ≤ ${GOAL_DD}\n")

    print("--- 1A: rr_tp sweep (be_at_rr=0, seed risk) ---")
    results_rrtp = {}
    for rr in [1.0, 1.25, 1.5, 1.75, 2.0, 2.25, 2.5]:
        s = _bench(f"rr_tp={rr}", {"rr_tp": rr})
        results_rrtp[rr] = s
    print()

    # Find best rr_tp candidates (those that may reach 50% WR with some DD budget)
    print("--- 1B: be_at_rr × rr_tp (only on rr_tp ≤ 2.0) ---")
    results_be = {}
    for rr in [1.0, 1.25, 1.5, 1.75, 2.0]:
        for be in [0.5, 1.0, 1.5, 2.0]:
            s = _bench(f"rr={rr} be={be}", {"rr_tp": rr, "be_at_rr": be})
            results_be[(rr, be)] = s
    print()

    # Risk crawl on best-WR config (likely rr_tp=1.0 or 1.25)
    print("--- 1C: risk sweep on rr_tp=1.0 ---")
    for risk in [0.003, 0.004, 0.005, 0.00625, 0.0075, 0.01, 0.0125, 0.015]:
        _bench(f"rr=1.0 risk={risk*100:.3f}%", {"rr_tp": 1.0}, risk=risk)
    print()

    print("--- 1D: risk sweep on rr_tp=1.25 ---")
    for risk in [0.003, 0.004, 0.005, 0.00625, 0.0075, 0.01, 0.0125, 0.015]:
        _bench(f"rr=1.25 risk={risk*100:.3f}%", {"rr_tp": 1.25}, risk=risk)
    print()

    print("--- 1E: risk sweep on rr_tp=1.5 ---")
    for risk in [0.003, 0.004, 0.005, 0.00625, 0.0075, 0.01, 0.0125, 0.015]:
        _bench(f"rr=1.5 risk={risk*100:.3f}%", {"rr_tp": 1.5}, risk=risk)
    print()


if __name__ == "__main__":
    main()
