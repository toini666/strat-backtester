"""Baseline replay — confirm the harness reproduces the preset's stored metrics.

Stored: PnL = -$25,532 / DD = $20,419 / N = 3,773 / WR = 50.25 %.
Tolerance: ±1 % on PnL and DD.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.goals._shared.harness import run_backtest, summarize, fmt_summary
from scripts.goals._shared.engine_settings import ui_default_engine_settings
from sweeps._campaign import (
    SEED_PARAMS, SEED_RISK, SEED_AUTO_CLOSE, SEED_BLACKOUTS,
    START, END, SYMBOL, INTERVAL, STRATEGY,
    INITIAL_EQUITY, MAX_CONTRACTS,
)


def _seed_engine_settings():
    es = ui_default_engine_settings(STRATEGY)
    # Match preset exactly: only 22:00-23:59 active. The UI override already
    # matches this — but reset all just in case.
    for w in es.blackout_windows:
        w.active = (w.start_hour, w.start_minute, w.end_hour, w.end_minute) in [
            (sh, sm, eh, em) for sh, sm, eh, em in SEED_BLACKOUTS
        ]
    es.auto_close_hour, es.auto_close_minute = SEED_AUTO_CLOSE
    return es


def main():
    print("=" * 90)
    print("BASELINE REPLAY")
    print("=" * 90)
    print(f"Period: {START} → {END}")
    print(f"Strategy: {STRATEGY} | Symbol: {SYMBOL} | Interval: {INTERVAL}")
    print(f"Risk: {SEED_RISK*100:.2f}% | Max contracts: {MAX_CONTRACTS}")
    print()

    es = _seed_engine_settings()
    active_bo = [(w.start_hour, w.start_minute, w.end_hour, w.end_minute)
                 for w in es.blackout_windows if w.active]
    print(f"Active blackouts: {active_bo}")
    print(f"Auto-close: {es.auto_close_hour:02d}:{es.auto_close_minute:02d}")
    print()

    r = run_backtest(
        strategy_name=STRATEGY,
        symbol=SYMBOL,
        interval=INTERVAL,
        start=START,
        end=END,
        strategy_params=SEED_PARAMS,
        initial_equity=INITIAL_EQUITY,
        risk_per_trade=SEED_RISK,
        max_contracts=MAX_CONTRACTS,
        engine_settings=es,
    )
    s = summarize(r)
    print("BASELINE:")
    print("  " + fmt_summary(s))
    print()

    # Stored metrics from data/presets.json (computed in the UI).
    # NOTE: total_return is in %; net $ = total_return / 100 * initial_equity.
    stored = {
        "net_pnl": -0.2553 * INITIAL_EQUITY,  # -25.53% × 50k = -$12,766
        "max_dd_$": 20418.80,
        "trades": 3773,
        "win_rate": 50.3,
    }
    print("STORED (from preset):")
    print(f"  PnL=${stored['net_pnl']:>9,.0f} | DD=${stored['max_dd_$']:>6,.0f} | "
          f"N={stored['trades']:>4} | WR={stored['win_rate']:>5.1f}%")
    print()

    pnl_diff = s["net_pnl"] - stored["net_pnl"]
    dd_diff = s["max_dd_$"] - stored["max_dd_$"]
    n_diff = s["trades"] - stored["trades"]
    print(f"DIFF: PnL={pnl_diff:+,.0f} | DD={dd_diff:+,.0f} | N={n_diff:+d}")

    pnl_ok = abs(pnl_diff) < 200.0
    dd_ok = abs(dd_diff) < 200.0
    n_ok = abs(n_diff) <= 5
    if pnl_ok and dd_ok and n_ok:
        print("\nBASELINE MATCH (within tolerance)")
    else:
        print("\nBASELINE MISMATCH — investigate before sweeping")
        sys.exit(1)


if __name__ == "__main__":
    main()
