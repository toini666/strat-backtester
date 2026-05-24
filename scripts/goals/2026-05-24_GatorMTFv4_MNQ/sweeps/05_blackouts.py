"""Sweep 5 — blackout combinations on the best combo from sweep 3.

Base: ABCD=1101 + rr=2.0 + cd=90 + amp=1.0 + ssl_mult=0.2 + tf=7.
Result: PnL=$23,540 / DD=$6,165.

Hour analysis says losing hours = 14, 16, 19, 23, 06.
Below-avg hours = 11, 12, 17, 20, 21, 22 (small or near-zero).

Test combinations:
  - single losing hour
  - cumulative losing hours
  - sub-hour windows around H14 (lunch / NY pre-open volatility)
  - aggressive: block all losers + below-avg
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
    SEED_PARAMS, SEED_RISK, SEED_AUTO_CLOSE, SEED_BLACKOUTS,
    START, END, SYMBOL, INTERVAL, STRATEGY,
    INITIAL_EQUITY, MAX_CONTRACTS,
)


BEST_PARAMS = {
    "final_rr": 2.0,
    "cooldown_bars": 90,
    "amp_mult": 1.0,
    "case_c_on": False,
}


def _engine(extra_active_hours):
    """Build engine with seed BO (22-23:59) + extra hour-level blackouts."""
    # Start from a fresh setting with seed blackouts only active.
    es = ui_default_engine_settings(STRATEGY)
    for w in es.blackout_windows:
        w.active = (w.start_hour, w.start_minute, w.end_hour, w.end_minute) in [
            (sh, sm, eh, em) for sh, sm, eh, em in SEED_BLACKOUTS
        ]
    es.auto_close_hour, es.auto_close_minute = SEED_AUTO_CLOSE

    # Apply extra hour-level blackouts (each is (sh, sm, eh, em)).
    extras = []
    for w in extra_active_hours:
        if isinstance(w, int):
            sh = w
            eh = w + 1
            em = 0
            if eh > 23:
                eh = 23
                em = 59
            extras.append({"start_hour": sh, "start_minute": 0,
                          "end_hour": eh, "end_minute": em})
        else:
            sh, sm, eh, em = w
            extras.append({"start_hour": sh, "start_minute": sm,
                          "end_hour": eh, "end_minute": em})

    es2 = make_engine_settings(
        STRATEGY,
        auto_close_hour=SEED_AUTO_CLOSE[0],
        auto_close_minute=SEED_AUTO_CLOSE[1],
        extra_active_windows=extras,
    )
    # Inherit ONLY the seed BO from es (deactivate all UI-default ones).
    for w in es2.blackout_windows:
        # Activate only the seed BO + our extras
        is_seed = (w.start_hour, w.start_minute, w.end_hour, w.end_minute) in [
            (sh, sm, eh, em) for sh, sm, eh, em in SEED_BLACKOUTS
        ]
        is_extra = any(
            (w.start_hour, w.start_minute, w.end_hour, w.end_minute) ==
            (e["start_hour"], e["start_minute"], e["end_hour"], e["end_minute"])
            for e in extras
        )
        w.active = is_seed or is_extra
    return es2


def run_one(label, extra_blackouts):
    params = dict(SEED_PARAMS)
    params.update(BEST_PARAMS)
    es = _engine(extra_blackouts)
    r = run_backtest(
        strategy_name=STRATEGY, symbol=SYMBOL, interval=INTERVAL,
        start=START, end=END,
        strategy_params=params,
        initial_equity=INITIAL_EQUITY, risk_per_trade=SEED_RISK,
        max_contracts=MAX_CONTRACTS,
        engine_settings=es,
    )
    s = summarize(r)
    print(f"{label:<55s} {fmt_summary(s)}")
    return s, [(w.start_hour, w.start_minute, w.end_hour, w.end_minute)
               for w in es.blackout_windows if w.active]


def main():
    print("=" * 90)
    print("SWEEP 5 — BLACKOUT COMBOS on best sweep 3 combo")
    print("=" * 90)

    results = []

    # A. Reference (no extra blackouts)
    print()
    print(">>> A. Reference (seed BO only)")
    s, _ = run_one("none", [])
    results.append(("none", s))

    # B. Single losing hour
    print()
    print(">>> B. Single losing-hour blackouts")
    for h in [14, 16, 19, 23, 6]:
        s, _ = run_one(f"+H{h:02d}", [h])
        results.append((f"+H{h:02d}", s))

    # C. Pairs of top 2-3 losing hours
    print()
    print(">>> C. Cumulative losing hours")
    cums = [
        ("+H14+H16",              [14, 16]),
        ("+H14+H19",              [14, 19]),
        ("+H16+H19",              [16, 19]),
        ("+H14+H16+H19",          [14, 16, 19]),
        ("+H14+H16+H19+H23",      [14, 16, 19, 23]),
        ("+H06+H14+H16+H19+H23",  [6, 14, 16, 19, 23]),
    ]
    for label, hrs in cums:
        s, _ = run_one(label, hrs)
        results.append((label, s))

    # D. Aggressive — block all sub-$500 hours
    print()
    print(">>> D. Aggressive (block losers + low-PnL)")
    aggressives = [
        ("+H14+H16+H19+H23+H06+H11+H12+H17+H21",
         [14, 16, 19, 23, 6, 11, 12, 17, 21]),
        ("+H14+H16+H19+H23+H06+H11+H12+H17+H20+H21+H22",
         [14, 16, 19, 23, 6, 11, 12, 17, 20, 21, 22]),
    ]
    for label, hrs in aggressives:
        s, _ = run_one(label, hrs)
        results.append((label, s))

    # E. Sub-hour windows (less aggressive)
    print()
    print(">>> E. Sub-hour windows")
    sub_combos = [
        ("+14:00-14:30",                [(14, 0, 14, 30)]),
        ("+14:00-15:00",                [(14, 0, 15, 0)]),
        ("+13:30-15:30",                [(13, 30, 15, 30)]),
        ("+15:30-16:00",                [(15, 30, 16, 0)]),
        ("+14:00-15:00 + 16:00-17:00",  [(14, 0, 15, 0), (16, 0, 17, 0)]),
        ("+14:00-15:00 + 16:00-17:00 + 19:00-20:00",
            [(14, 0, 15, 0), (16, 0, 17, 0), (19, 0, 20, 0)]),
    ]
    for label, hrs in sub_combos:
        s, _ = run_one(label, hrs)
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
    print("RANKED — DD ≤ $4,000")
    ok4 = [(l, s) for l, s in results if s["max_dd_$"] <= 4000.0]
    ok4.sort(key=lambda x: -x[1]["net_pnl"])
    for l, s in ok4[:20]:
        print(f"  {l:<55s} {fmt_summary(s)}")

    print()
    print("BEST DD (top 10)")
    by_dd = sorted(results, key=lambda x: x[1]["max_dd_$"])
    for l, s in by_dd[:10]:
        print(f"  {l:<55s} {fmt_summary(s)}")

    print()
    print("BEST PnL (top 10)")
    by_pnl = sorted(results, key=lambda x: -x[1]["net_pnl"])
    for l, s in by_pnl[:10]:
        print(f"  {l:<55s} {fmt_summary(s)}")


if __name__ == "__main__":
    main()
