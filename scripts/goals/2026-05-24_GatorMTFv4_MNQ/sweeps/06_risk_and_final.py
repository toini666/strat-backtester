"""Sweep 6 — risk sweep + final fine-tuning around the winning combo.

Once a blackout combo is picked, dial risk_per_trade to maximize PnL
while keeping DD ≤ $2,500. Also try a few small variations of strategy
params to grease in the final result.
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
    SEED_PARAMS, SEED_AUTO_CLOSE, SEED_BLACKOUTS,
    START, END, SYMBOL, INTERVAL, STRATEGY,
    INITIAL_EQUITY, MAX_CONTRACTS,
)


BEST_PARAMS = {
    "final_rr": 2.0,
    "cooldown_bars": 90,
    "amp_mult": 1.0,
    "case_c_on": False,
}

# From sweep 5 winner: aggressive 9-hour blackout set
# +H14+H16+H19+H23+H06+H11+H12+H17+H21 → PnL=$29,329 / DD=$5,740 / PF=1.15
WINNING_BLACKOUTS = [
    (22, 0, 23, 59),   # seed (auto-close adjacent)
    (6, 0, 7, 0),      # H06
    (11, 0, 12, 0),    # H11
    (12, 0, 13, 0),    # H12
    (14, 0, 15, 0),    # H14
    (16, 0, 17, 0),    # H16
    (17, 0, 18, 0),    # H17
    (19, 0, 20, 0),    # H19
    (21, 0, 22, 0),    # H21
    (23, 0, 23, 59),   # H23 (capped at 23:59)
]


def _engine(blackouts):
    extras = [{"start_hour": sh, "start_minute": sm,
               "end_hour": eh, "end_minute": em}
              for sh, sm, eh, em in blackouts
              if (sh, sm, eh, em) != (22, 0, 23, 59)]
    es = make_engine_settings(
        STRATEGY,
        auto_close_hour=SEED_AUTO_CLOSE[0],
        auto_close_minute=SEED_AUTO_CLOSE[1],
        extra_active_windows=extras,
    )
    seed_set = {(sh, sm, eh, em) for sh, sm, eh, em in [(22, 0, 23, 59)]}
    extra_set = {(e["start_hour"], e["start_minute"], e["end_hour"], e["end_minute"])
                 for e in extras}
    for w in es.blackout_windows:
        key = (w.start_hour, w.start_minute, w.end_hour, w.end_minute)
        w.active = key in seed_set or key in extra_set
    return es


def run_one(label, risk_pct, **overrides):
    params = dict(SEED_PARAMS)
    params.update(BEST_PARAMS)
    params.update(overrides)
    r = run_backtest(
        strategy_name=STRATEGY, symbol=SYMBOL, interval=INTERVAL,
        start=START, end=END,
        strategy_params=params,
        initial_equity=INITIAL_EQUITY,
        risk_per_trade=risk_pct / 100.0,
        max_contracts=MAX_CONTRACTS,
        engine_settings=_engine(WINNING_BLACKOUTS),
    )
    s = summarize(r)
    print(f"{label:<55s} {fmt_summary(s)}")
    return s


def main():
    print("=" * 90)
    print("SWEEP 6 — RISK SWEEP + FINAL FINE-TUNING")
    print(f"Base params: {BEST_PARAMS}")
    print(f"Active blackouts: {WINNING_BLACKOUTS}")
    print("=" * 90)

    results = []

    # A. Risk sweep
    print()
    print(">>> A. Risk sweep")
    for r_pct in [0.20, 0.25, 0.30, 0.35, 0.40, 0.45, 0.50, 0.60, 0.75, 1.0]:
        label = f"risk={r_pct}%"
        s = run_one(label, r_pct)
        s["risk"] = r_pct
        results.append((label, s))

    # B. Final fine-tuning: re-test small ssl_mult / cooldown / rr variations
    #    around the winner, at best risk level (will be determined dynamically)
    # For now: lock risk at 0.5% (seed) and test small params nudges.
    print()
    print(">>> B. Final fine-tuning at risk=0.5%")
    for ssl_m, cd, rr in [
        (0.18, 90, 2.0),
        (0.20, 75, 2.0),
        (0.20, 90, 1.9),
        (0.20, 90, 2.1),
        (0.20, 100, 2.0),
        (0.22, 90, 2.0),
    ]:
        label = f"sslm={ssl_m} cd={cd} rr={rr}"
        s = run_one(label, 0.50, ssl_mult=ssl_m, cooldown_bars=cd, final_rr=rr)
        results.append((label, s))

    print()
    print("=" * 90)
    print("RANKED RESULTS — DD ≤ $2,500 by PnL")
    print("=" * 90)
    ok = [(l, s) for l, s in results if s["max_dd_$"] <= 2500.0]
    ok.sort(key=lambda x: -x[1]["net_pnl"])
    for l, s in ok[:30]:
        print(f"  {l:<55s} {fmt_summary(s)}")

    print()
    print("RANKED — DD ≤ $3,000")
    ok3 = [(l, s) for l, s in results if s["max_dd_$"] <= 3000.0]
    ok3.sort(key=lambda x: -x[1]["net_pnl"])
    for l, s in ok3[:20]:
        print(f"  {l:<55s} {fmt_summary(s)}")

    print()
    print("BEST PnL (top 10)")
    by_pnl = sorted(results, key=lambda x: -x[1]["net_pnl"])
    for l, s in by_pnl[:10]:
        print(f"  {l:<55s} {fmt_summary(s)}")


if __name__ == "__main__":
    main()
