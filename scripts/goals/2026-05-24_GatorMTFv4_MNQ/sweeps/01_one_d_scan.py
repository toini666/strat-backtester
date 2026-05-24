"""Sweep 1 — 1-D scan of each strategy param around the seed.

Goal: identify the levers that move PnL/DD the most. Around 130 sims.

Baseline: PnL=-$12,766 | DD=$20,419 | N=3,773 | WR=50.3% | PF=0.97.
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


def _engine():
    es = ui_default_engine_settings(STRATEGY)
    for w in es.blackout_windows:
        w.active = (w.start_hour, w.start_minute, w.end_hour, w.end_minute) in [
            (sh, sm, eh, em) for sh, sm, eh, em in SEED_BLACKOUTS
        ]
    es.auto_close_hour, es.auto_close_minute = SEED_AUTO_CLOSE
    return es


def run_one(label: str, **param_overrides):
    params = dict(SEED_PARAMS)
    params.update(param_overrides)
    r = run_backtest(
        strategy_name=STRATEGY,
        symbol=SYMBOL,
        interval=INTERVAL,
        start=START,
        end=END,
        strategy_params=params,
        initial_equity=INITIAL_EQUITY,
        risk_per_trade=SEED_RISK,
        max_contracts=MAX_CONTRACTS,
        engine_settings=_engine(),
    )
    s = summarize(r)
    print(f"{label:<55s} {fmt_summary(s)}")
    return s


# Scans — each list is a 1-D sweep around the seed.
SCANS = {
    "final_rr":               [0.8, 1.0, 1.25, 1.5, 1.75, 2.0, 2.5, 3.0],
    "cooldown_bars":          [3, 7, 14, 21, 30, 60, 120],
    "sl_lookback":            [1, 3, 5, 10, 15],
    "sl_min_pct":             [0.05, 0.10, 0.15, 0.25, 0.40, 0.60],
    "tick_buffer":            [0, 2, 4, 8],
    "entry_window_bars_trigger": [1, 2, 3, 5, 8, 12],
    "amp_mult":               [1.0, 1.5, 2.0, 2.5, 3.0, 4.0],
    "ema_len":                [3, 5, 7, 9, 14],
    "hma1_len":               [7, 9, 13, 17, 21],
    "hma2_len":               [13, 17, 21, 28, 34],
    "ssl_len":                [30, 40, 60, 80, 120],
    "ssl_mult":               [0.10, 0.15, 0.20, 0.25, 0.40],
    "mf_length":              [14, 21, 35, 50, 70],
    "mf_smooth":              [3, 6, 10, 14],
    "hyper_wave_length":      [3, 5, 7, 10],
    "signal_length":          [2, 3, 4, 6],
    "sig_extreme_threshold":  [10.0, 15.0, 20.0, 30.0, 40.0],
    "trigger_tf_minutes":     [3, 5, 7, 10, 15],
}


def main():
    print("=" * 90)
    print("SWEEP 1 — 1-D SCAN OF STRATEGY PARAMS")
    print("=" * 90)

    # Seed reference run
    print()
    print(">>> SEED (reference)")
    seed_s = run_one("SEED", )
    print()

    all_results = {"SEED": seed_s}

    for param_name, values in SCANS.items():
        print(f">>> Scan: {param_name}")
        for v in values:
            label = f"{param_name}={v}"
            s = run_one(label, **{param_name: v})
            all_results[label] = s
        print()

    # Final ranking by PnL (DD ≤ 2500 first, then top PnL)
    print("=" * 90)
    print("TOP RESULTS (DD ≤ $2,500, ranked by PnL)")
    print("=" * 90)
    ok = [(lbl, s) for lbl, s in all_results.items() if s["max_dd_$"] <= 2500.0]
    ok.sort(key=lambda x: -x[1]["net_pnl"])
    for lbl, s in ok[:30]:
        print(f"  {lbl:<50s} {fmt_summary(s)}")

    print()
    print("BEST PnL (DD-unconstrained, top 20)")
    all_sorted = sorted(all_results.items(), key=lambda x: -x[1]["net_pnl"])
    for lbl, s in all_sorted[:20]:
        print(f"  {lbl:<50s} {fmt_summary(s)}")

    print()
    print("BEST DD (top 20)")
    by_dd = sorted(all_results.items(), key=lambda x: x[1]["max_dd_$"])
    for lbl, s in by_dd[:20]:
        print(f"  {lbl:<50s} {fmt_summary(s)}")


if __name__ == "__main__":
    main()
