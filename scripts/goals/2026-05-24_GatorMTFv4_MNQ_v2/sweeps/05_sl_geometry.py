"""Phase 5 — SL geometry combo at new best (rr=1.5, cd=90).

v1 dismissed SL geometry as "ineffective" in 1-D — but at rr=1.5 (vs v1's 2.0)
the optimum likely shifts (memory: feedback_sl_lookback_rr_interaction).

Two stages:
  A) 1-D rescan of each axis at rr=1.5: sl_lookback (6) + sl_min_pct (6) + tick_buffer (5) = 17 sims
  B) 2-D refinement on the top 2 movers (~16 sims)
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

BEST_CONFIG = {
    "amp_mult": 1.5, "hma1_len": 13, "hma2_len": 21,
    "case_a_on": True, "case_b_on": True,
    "case_c_on": False, "case_d_on": True,
    "final_rr": 1.5, "cooldown_bars": 90,
}


def _es_no_blackouts():
    es = ui_default_engine_settings(STRATEGY)
    for w in es.blackout_windows:
        w.active = False
    es.auto_close_hour, es.auto_close_minute = AUTO_CLOSE
    return es


def _run(params, es, label):
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
    print("PHASE 5 — SL geometry at rr=1.5 cd=90")
    print("=" * 100)
    es = _es_no_blackouts()
    SEED = dict(V1_WINNER_PARAMS)
    SEED.update(BEST_CONFIG)

    # ---- Stage A: 1-D ----
    sweeps = [
        ("sl_lookback", [1, 2, 3, 5, 7, 10, 15]),
        ("sl_min_pct",  [0.05, 0.10, 0.15, 0.20, 0.30, 0.40, 0.60]),
        ("tick_buffer", [0, 1, 2, 4, 6, 8]),
    ]

    all_rows = []
    t_start = time.time()
    for axis, vals in sweeps:
        print()
        print(f"--- 1-D: {axis} ---")
        for v in vals:
            p = dict(SEED)
            p[axis] = v
            marker = "  ← seed" if v == V1_WINNER_PARAMS[axis] else ""
            s = _run(p, es, label=f"{axis}={v}{marker}")
            all_rows.append({"axis": axis, "value": v, **s})

    print()
    print(f"Stage A elapsed: {(time.time() - t_start)/60:.1f} min")

    # ---- Identify the 2 movers ----
    print()
    print("Stage A best per axis (PnL/DD ratio):")
    movers = []
    by_axis = {}
    for r in all_rows:
        by_axis.setdefault(r["axis"], []).append(r)
    for axis, rows in by_axis.items():
        rows_valid = [r for r in rows if r["max_dd_$"] > 0]
        rows_valid.sort(key=lambda x: x["net_pnl"] / x["max_dd_$"], reverse=True)
        best = rows_valid[0]
        seed_val = V1_WINNER_PARAMS[axis]
        seed_row = next((r for r in rows_valid if r["value"] == seed_val), None)
        delta = best["net_pnl"] - (seed_row["net_pnl"] if seed_row else 0)
        ratio = best["net_pnl"] / best["max_dd_$"]
        print(f"  {axis:<12s} best={best['value']}  Δ_PnL_vs_seed=${delta:+,.0f}  "
              f"ratio={ratio:.2f}×  PF={best['profit_factor']}")
        movers.append((axis, best["value"], abs(delta)))

    # ---- Stage B: 2-D on top 2 movers ----
    movers.sort(key=lambda x: x[2], reverse=True)
    a1, a2 = movers[0][0], movers[1][0]
    print()
    print(f"Top 2 movers: {a1}, {a2}  →  2-D combo")

    vals_a1 = next(v for axis, v in sweeps if axis == a1)
    vals_a2 = next(v for axis, v in sweeps if axis == a2)

    # Trim to top 4 values per axis
    a1_top4 = sorted(
        [(r["value"], r["net_pnl"] / max(r["max_dd_$"], 1)) for r in by_axis[a1]],
        key=lambda x: x[1], reverse=True
    )[:4]
    a2_top4 = sorted(
        [(r["value"], r["net_pnl"] / max(r["max_dd_$"], 1)) for r in by_axis[a2]],
        key=lambda x: x[1], reverse=True
    )[:4]
    a1_vals = [v for v, _ in a1_top4]
    a2_vals = [v for v, _ in a2_top4]
    print(f"  {a1} ∈ {a1_vals}  ×  {a2} ∈ {a2_vals}  = {len(a1_vals)*len(a2_vals)} sims")

    print()
    print(f"--- 2-D: {a1} × {a2} ---")
    combo_rows = []
    for v1 in a1_vals:
        for v2 in a2_vals:
            p = dict(SEED)
            p[a1] = v1
            p[a2] = v2
            s = _run(p, es, label=f"{a1}={v1} {a2}={v2}")
            combo_rows.append({a1: v1, a2: v2, **s})

    print()
    print(f"Total elapsed: {(time.time() - t_start)/60:.1f} min  "
          f"({len(all_rows) + len(combo_rows)} sims)")

    print()
    print("Top 5 combos by PnL/DD ratio:")
    combo_valid = [r for r in combo_rows if r["max_dd_$"] > 0]
    combo_valid.sort(key=lambda x: x["net_pnl"] / x["max_dd_$"], reverse=True)
    for r in combo_valid[:5]:
        ratio = r["net_pnl"] / r["max_dd_$"]
        v1 = r[a1]
        v2 = r[a2]
        print(f"  {a1}={v1:<6} {a2}={v2:<6}  PnL=${r['net_pnl']:>8,.0f}  DD=${r['max_dd_$']:>6,.0f}  "
              f"ratio={ratio:.2f}×  PF={r['profit_factor']}")


if __name__ == "__main__":
    main()
