"""Phase 2 — HMA stack 1-D scan.

Sweep ema_len, hma1_len, hma2_len, amp_mult one at a time around the v1
winner. ~28 sims total. Goal: identify which HMA axis moves PF.

v1 never touched ema_len, hma1_len, hma2_len; only amp_mult (1.0 vs 2.0).
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.goals._shared.harness import run_backtest, summarize, fmt_summary
from scripts.goals._shared.engine_settings import ui_default_engine_settings
from sweeps._campaign import (
    V1_WINNER_PARAMS, SWEEP_RISK, AUTO_CLOSE,
    START, END, SYMBOL, INTERVAL, STRATEGY,
    INITIAL_EQUITY, MAX_CONTRACTS,
)


def _es_no_blackouts():
    es = ui_default_engine_settings(STRATEGY)
    for w in es.blackout_windows:
        w.active = False
    es.auto_close_hour, es.auto_close_minute = AUTO_CLOSE
    return es


def main():
    print("=" * 100)
    print("PHASE 2 — HMA stack 1-D scan")
    print("=" * 100)

    es = _es_no_blackouts()
    SEED = dict(V1_WINNER_PARAMS)

    sweeps = [
        ("ema_len",  [4, 5, 7, 9, 12, 16]),
        ("hma1_len", [7, 9, 13, 17, 21, 26]),
        ("hma2_len", [13, 17, 21, 28, 35, 50]),
        ("amp_mult", [0.5, 0.75, 1.0, 1.25, 1.5, 2.0, 2.5, 3.0]),
    ]

    all_rows = []
    t_start = time.time()
    for axis, values in sweeps:
        print()
        print(f"--- Sweep: {axis} ---")
        for v in values:
            params = dict(SEED)
            params[axis] = v
            t0 = time.time()
            try:
                r = run_backtest(
                    strategy_name=STRATEGY,
                    symbol=SYMBOL, interval=INTERVAL,
                    start=START, end=END,
                    strategy_params=params,
                    initial_equity=INITIAL_EQUITY,
                    risk_per_trade=SWEEP_RISK,
                    max_contracts=MAX_CONTRACTS,
                    engine_settings=es,
                )
                s = summarize(r)
                marker = "  ← seed" if v == V1_WINNER_PARAMS[axis] else ""
                label = f"{axis}={v}"
                print(f"  {label:<18s} {fmt_summary(s)}{marker}")
                all_rows.append({"axis": axis, "value": v, **s})
            except Exception as exc:
                print(f"  {axis}={v}  ERROR: {exc}")

    print()
    print(f"Total elapsed: {(time.time() - t_start)/60:.1f} min  ({len(all_rows)} sims)")
    print()

    # ---- Best by PnL/DD per axis ----
    print("=" * 100)
    print("Best value per axis (by PnL/DD ratio):")
    print("=" * 100)
    by_axis = {}
    for r in all_rows:
        by_axis.setdefault(r["axis"], []).append(r)
    for axis, rows in by_axis.items():
        rows_valid = [r for r in rows if r["max_dd_$"] > 0]
        rows_valid.sort(key=lambda x: x["net_pnl"] / x["max_dd_$"], reverse=True)
        best = rows_valid[0]
        ratio = best["net_pnl"] / best["max_dd_$"]
        print(f"  {axis:<10s} best={best['value']}  "
              f"PnL=${best['net_pnl']:>9,.0f}  DD=${best['max_dd_$']:>6,.0f}  "
              f"ratio={ratio:.2f}×  PF={best['profit_factor']}")


if __name__ == "__main__":
    main()
