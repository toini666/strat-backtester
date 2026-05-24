"""Phase 2B — amp_mult × hma1_len 2-D + hma2_len sub-sweep.

1-D scan in Phase 2 found:
  - amp_mult=1.5 → PnL $28,461 / DD $6,850 / PF 1.11 (vs seed 1.0 → $18,026)
  - hma1_len=26 → PnL $24,244 / DD $7,170 / PF 1.10 (vs seed 13)
  - hma1_len=21 collapses (h1==h2 degenerate)

Combine: amp_mult ∈ {1.0,1.25,1.5,2.0} × hma1_len ∈ {13,17,22,26,30}
= 20 sims. Then for the best (amp, h1), sweep hma2_len ∈ {17,21,28,35,42}.
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


def _run(params, es, label=""):
    t0 = time.time()
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
    s["elapsed_s"] = round(time.time() - t0, 1)
    print(f"  {label:<28s} {fmt_summary(s)}  ({s['elapsed_s']}s)")
    return s


def main():
    print("=" * 100)
    print("PHASE 2B — amp_mult × hma1_len combo, then hma2_len sub-sweep")
    print("=" * 100)
    es = _es_no_blackouts()
    SEED = dict(V1_WINNER_PARAMS)

    # ---- Stage A: amp_mult × hma1_len ----
    amp_list = [1.0, 1.25, 1.5, 2.0]
    h1_list = [9, 13, 17, 22, 26, 30]
    rows = []
    t_start = time.time()
    print()
    print(f"--- 2-D: amp_mult × hma1_len  ({len(amp_list)*len(h1_list)} sims) ---")
    for amp in amp_list:
        for h1 in h1_list:
            p = dict(SEED)
            p["amp_mult"] = amp
            p["hma1_len"] = h1
            # Skip degenerate (hma1 == hma2)
            if h1 == p["hma2_len"]:
                print(f"  amp={amp} h1={h1}  SKIP degenerate (h1==h2)")
                continue
            s = _run(p, es, label=f"amp={amp} h1={h1}")
            rows.append({"amp": amp, "h1": h1, **s})

    print()
    print("Top 5 (amp × h1) by PnL/DD ratio:")
    rows_valid = [r for r in rows if r["max_dd_$"] > 0]
    rows_valid.sort(key=lambda x: x["net_pnl"] / x["max_dd_$"], reverse=True)
    for r in rows_valid[:5]:
        ratio = r["net_pnl"] / r["max_dd_$"]
        print(f"  amp={r['amp']:<5} h1={r['h1']:<3} "
              f"PnL=${r['net_pnl']:>8,.0f}  DD=${r['max_dd_$']:>6,.0f}  "
              f"ratio={ratio:.2f}×  PF={r['profit_factor']}")
    best = rows_valid[0]

    # ---- Stage B: hma2_len sub-sweep at best (amp, h1) ----
    print()
    print(f"--- hma2_len sub-sweep at amp={best['amp']} h1={best['h1']} ---")
    h2_list = [17, 21, 28, 35, 42, 50]
    rows2 = []
    for h2 in h2_list:
        if h2 == best["h1"]:
            print(f"  h2={h2}  SKIP degenerate")
            continue
        p = dict(SEED)
        p["amp_mult"] = best["amp"]
        p["hma1_len"] = best["h1"]
        p["hma2_len"] = h2
        s = _run(p, es, label=f"h2={h2}")
        rows2.append({"h2": h2, **s})

    print()
    print(f"Total elapsed: {(time.time() - t_start)/60:.1f} min  "
          f"({len(rows) + len(rows2)} sims)")

    print()
    print("Final best (sub-sweep + combo):")
    all_results = rows + rows2
    all_valid = [r for r in all_results if r["max_dd_$"] > 0]
    all_valid.sort(key=lambda x: x["net_pnl"] / x["max_dd_$"], reverse=True)
    for r in all_valid[:3]:
        ratio = r["net_pnl"] / r["max_dd_$"]
        amp = r.get("amp", best["amp"])
        h1 = r.get("h1", best["h1"])
        h2 = r.get("h2", SEED["hma2_len"])
        print(f"  amp={amp} h1={h1} h2={h2}  "
              f"PnL=${r['net_pnl']:>8,.0f}  DD=${r['max_dd_$']:>6,.0f}  "
              f"ratio={ratio:.2f}×  PF={r['profit_factor']}")


if __name__ == "__main__":
    main()
