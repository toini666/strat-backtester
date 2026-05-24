"""Phase 1 — trigger_tf_minutes × entry_window_bars_trigger sweep.

The biggest unexplored lever from v1. v1 kept trigger_tf=7 throughout.
Sweep: trigger_tf ∈ {2,3,5,7,10,15} × window_bars_trigger ∈ {3,5,8} = 18 sims.
All other params at v1 winner; no blackouts; risk 0.5 %.

Report Pareto frontier (PnL @ DD ≤ goal × 2.5 = $6,250 sweep-budget).
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
    print("PHASE 1 — trigger_tf_minutes × entry_window_bars_trigger sweep")
    print("=" * 100)
    print(f"Period: {START} → {END}  |  risk: {SWEEP_RISK*100:.2f}%  |  no blackouts")
    print()

    es = _es_no_blackouts()
    tfs = [2, 3, 5, 7, 10, 15]
    windows = [3, 5, 8]

    rows = []
    t_start = time.time()
    for tf in tfs:
        for wb in windows:
            params = dict(V1_WINNER_PARAMS)
            params["trigger_tf_minutes"] = tf
            params["entry_window_bars_trigger"] = wb
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
                s["label"] = f"tf={tf:>2}m  wb={wb}"
                s["elapsed_s"] = round(time.time() - t0, 1)
                rows.append({"tf": tf, "wb": wb, **s})
                print(f"{s['label']:<18s} {fmt_summary(s)}  ({s['elapsed_s']}s)")
            except Exception as exc:
                print(f"tf={tf:>2}m  wb={wb}  ERROR: {exc}")

    print()
    print(f"Total elapsed: {(time.time() - t_start)/60:.1f} min")
    print()

    # ---- Ranking ----
    print("=" * 100)
    print("TOP 5 by PnL (no DD filter):")
    print("=" * 100)
    rows_sorted = sorted(rows, key=lambda x: x["net_pnl"], reverse=True)
    for r in rows_sorted[:5]:
        print(f"  tf={r['tf']:>2}m wb={r['wb']}  "
              f"PnL=${r['net_pnl']:>9,.0f}  DD=${r['max_dd_$']:>6,.0f}  "
              f"N={r['trades']:>4}  WR={r['win_rate']:>4.1f}%  PF={r['profit_factor']}")

    print()
    print("=" * 100)
    print("TOP 5 by PnL/DD ratio (the real objective):")
    print("=" * 100)
    rows_by_ratio = sorted(
        [r for r in rows if r["max_dd_$"] > 0],
        key=lambda x: x["net_pnl"] / x["max_dd_$"], reverse=True,
    )
    for r in rows_by_ratio[:5]:
        ratio = r["net_pnl"] / r["max_dd_$"] if r["max_dd_$"] > 0 else 0
        print(f"  tf={r['tf']:>2}m wb={r['wb']}  "
              f"PnL=${r['net_pnl']:>9,.0f}  DD=${r['max_dd_$']:>6,.0f}  "
              f"ratio={ratio:.2f}×  WR={r['win_rate']:>4.1f}%  PF={r['profit_factor']}")


if __name__ == "__main__":
    main()
