"""Phase 2 — Tighten entry quality on the new rr_tp=1.25 anchor.

New ANCHOR (Phase 1 winner): rr_tp=1.25, everything else = seed v4.
  PnL=$39,404 / DD=$2,171 / WR=53.7% / N=791 / PF=1.39

DD budget headroom: $2500 - $2171 = $329 → room to push PnL.

Sweep:
- long_threshold / short_threshold ∈ {4..8}
- min_gap ∈ {6..14}
- max_candle_pct ∈ {0.15, 0.20, 0.25, 0.30, 0.40}
- Each tested ALONE first (vs anchor).
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


# Phase 1 anchor
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


def _bench(label: str, params_override: dict, risk: float = ANCHOR_RISK):
    params = dict(SEED_PARAMS)
    params.update(ANCHOR)
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
    print(f"=== Phase 2 — Entry quality tightening (anchor: rr_tp=1.25) ===\n")
    print(f"Goal: WR ≥ {GOAL_WR}% / DD ≤ ${GOAL_DD}\n")

    print("--- Anchor recheck ---")
    _bench("ANCHOR (rr_tp=1.25)", {})
    print()

    print("--- 2A: long_threshold sweep ---")
    for lt in [4, 5, 6, 7, 8]:
        _bench(f"long_threshold={lt}", {"long_threshold": lt})
    print()

    print("--- 2B: short_threshold sweep ---")
    for st in [4, 5, 6, 7, 8]:
        _bench(f"short_threshold={st}", {"short_threshold": st})
    print()

    print("--- 2C: both thresholds together ---")
    for t in [4, 5, 6, 7, 8]:
        _bench(f"long=short={t}", {"long_threshold": t, "short_threshold": t})
    print()

    print("--- 2D: min_gap sweep ---")
    for mg in [6, 7, 8, 9, 10, 11, 12, 13, 14]:
        _bench(f"min_gap={mg}", {"min_gap": mg})
    print()

    print("--- 2E: max_candle_pct sweep ---")
    for mc in [0.10, 0.15, 0.20, 0.25, 0.30, 0.40, 0.50, 0.60]:
        _bench(f"max_candle_pct={mc}", {"max_candle_pct": mc})
    print()

    print("--- 2F: prep thresholds (V1 carry — may or may not gate) ---")
    for pt in [2, 3, 4, 5]:
        _bench(f"long_prep=short_prep={pt}",
               {"long_prep_threshold": pt, "short_prep_threshold": pt})
    print()


if __name__ == "__main__":
    main()
