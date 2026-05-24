"""Sweep 7 — finer risk grid between 0.25% and 0.30% to push PnL.

Sweep 6 showed risk=0.25% → DD $2,212 (under budget) and risk=0.30% → DD $3,740 (over).
Non-linear due to integer contract rounding. Try 0.26, 0.27, 0.28, 0.29.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.goals._shared.harness import run_backtest, summarize, fmt_summary
from scripts.goals._shared.engine_settings import make_engine_settings
from sweeps._campaign import (
    SEED_PARAMS, SEED_AUTO_CLOSE,
    START, END, SYMBOL, INTERVAL, STRATEGY,
    INITIAL_EQUITY, MAX_CONTRACTS,
)


BEST_PARAMS = {
    "final_rr": 2.0,
    "cooldown_bars": 90,
    "amp_mult": 1.0,
    "case_c_on": False,
}

WINNING_BLACKOUTS = [
    (22, 0, 23, 59),
    (6, 0, 7, 0),
    (11, 0, 12, 0),
    (12, 0, 13, 0),
    (14, 0, 15, 0),
    (16, 0, 17, 0),
    (17, 0, 18, 0),
    (19, 0, 20, 0),
    (21, 0, 22, 0),
    (23, 0, 23, 59),
]


def _engine():
    extras = [{"start_hour": sh, "start_minute": sm,
               "end_hour": eh, "end_minute": em}
              for sh, sm, eh, em in WINNING_BLACKOUTS
              if (sh, sm, eh, em) != (22, 0, 23, 59)]
    es = make_engine_settings(
        STRATEGY,
        auto_close_hour=SEED_AUTO_CLOSE[0],
        auto_close_minute=SEED_AUTO_CLOSE[1],
        extra_active_windows=extras,
    )
    seed_set = {(22, 0, 23, 59)}
    extra_set = {(e["start_hour"], e["start_minute"], e["end_hour"], e["end_minute"])
                 for e in extras}
    for w in es.blackout_windows:
        key = (w.start_hour, w.start_minute, w.end_hour, w.end_minute)
        w.active = key in seed_set or key in extra_set
    return es


def run_one(label, risk_pct):
    params = dict(SEED_PARAMS)
    params.update(BEST_PARAMS)
    r = run_backtest(
        strategy_name=STRATEGY, symbol=SYMBOL, interval=INTERVAL,
        start=START, end=END,
        strategy_params=params,
        initial_equity=INITIAL_EQUITY,
        risk_per_trade=risk_pct / 100.0,
        max_contracts=MAX_CONTRACTS,
        engine_settings=_engine(),
    )
    s = summarize(r)
    s["risk"] = risk_pct
    print(f"{label:<55s} {fmt_summary(s)}")
    return s


def main():
    print("=" * 90)
    print("SWEEP 7 — FINER RISK GRID 0.24-0.32")
    print("=" * 90)
    results = []
    for r_pct in [0.24, 0.25, 0.26, 0.27, 0.28, 0.29, 0.30, 0.31, 0.32]:
        s = run_one(f"risk={r_pct}%", r_pct)
        results.append(s)

    print()
    print("RANKED — DD ≤ $2,500 (highest risk first)")
    ok = [s for s in results if s["max_dd_$"] <= 2500.0]
    ok.sort(key=lambda x: -x["risk"])
    for s in ok:
        print(f"  risk={s['risk']:.2f}%  {fmt_summary(s)}")


if __name__ == "__main__":
    main()
