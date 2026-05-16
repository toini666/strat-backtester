"""Sweep 03 — Strategy params 1D for HMASSLOsciV2.

Base: best filter combo from 02b (delta_ext + cloud_zero + sig_extreme).
1D sweep on every meaningful hyperparam — record ratio_p_dd lift vs base.
"""

from __future__ import annotations

import json
from pathlib import Path

from _campaign import (
    DEFAULT_RISK,
    END,
    INITIAL_EQUITY,
    MAX_CONTRACTS,
    START,
    STRATEGY,
    SYMBOL,
)

from scripts.goals._shared.harness import bench


TF = "7m"
BASE = {
    "delta_ext_on": True,
    "cloud_zero_on": True,
    "sig_extreme_on": True,
}

# 1D sweeps — (param, [values_to_test])
SWEEPS = [
    ("ema_len", [5, 7, 9, 11, 13]),
    ("hma1_len", [9, 13, 17, 21, 25]),
    ("hma2_len", [17, 21, 25, 29, 34, 42]),
    ("amp_mult", [1.0, 1.5, 2.0, 2.5, 3.0]),
    ("hma_pol_bars", [0, 1, 3, 5, 7]),
    ("ssl_len", [30, 40, 60, 80, 100]),
    ("ssl_mult", [0.1, 0.2, 0.3, 0.5]),
    ("hyper_wave_length", [3, 5, 7, 9]),
    ("signal_length", [2, 3, 4, 5]),
    ("mf_length", [25, 35, 45, 55]),
    ("mf_smooth", [3, 6, 9, 12]),
    ("sig_extreme", [10.0, 15.0, 20.0, 25.0, 30.0, 35.0]),
    ("hw_extreme", [10.0, 15.0, 20.0, 25.0, 30.0]),
    ("hw_range", [5.0, 10.0, 15.0, 20.0]),
    ("max_sl_points", [100.0, 200.0, 300.0, 500.0]),
    ("cooldown_bars", [0, 1, 2, 3, 5]),
    ("max_candle_pct", [0.0, 0.5, 0.7, 0.9, 1.5]),
    ("tick_buffer", [0, 1, 2, 3]),
    ("sl_mode", ["cross_hma", "ssl_extreme", "mix"]),
    ("exit_mode", ["both_hma", "break_hma", "inversion_hma"]),
    ("hw_partial_pct", [0.0, 25.0, 50.0]),
    ("hw_partial_min_rr", [0.0, 0.5, 1.0]),
]


def main():
    print(f"=== Sweep 03: strategy params 1D — {STRATEGY} / {SYMBOL} / {TF} ===")
    print(f"    BASE = {BASE}")
    print()

    base = bench(
        label="BASE",
        strategy_name=STRATEGY, symbol=SYMBOL, interval=TF,
        start=START, end=END, strategy_params=BASE,
        initial_equity=INITIAL_EQUITY, risk_per_trade=DEFAULT_RISK,
        max_contracts=MAX_CONTRACTS,
    )
    base["ratio_p_dd"] = round(base["net_pnl"] / base["max_dd_$"], 2) if base["max_dd_$"] > 0 else None
    base_ratio = base["ratio_p_dd"]
    print()

    all_rows = [{"label": "BASE", "param": None, "value": None, **base}]
    best_per_param = []

    for param, values in SWEEPS:
        print(f"\n--- 1D sweep: {param} ---")
        rows_p = []
        for val in values:
            params = {**BASE, param: val}
            s = bench(
                label=f"{param}={val}",
                strategy_name=STRATEGY, symbol=SYMBOL, interval=TF,
                start=START, end=END, strategy_params=params,
                initial_equity=INITIAL_EQUITY, risk_per_trade=DEFAULT_RISK,
                max_contracts=MAX_CONTRACTS,
            )
            s["ratio_p_dd"] = round(s["net_pnl"] / s["max_dd_$"], 2) if s["max_dd_$"] > 0 else None
            s["param"], s["value"] = param, val
            rows_p.append(s)
            all_rows.append(s)
        # find best in this 1D
        best = max(rows_p, key=lambda r: r["ratio_p_dd"] or -999)
        delta = (best["ratio_p_dd"] or 0) - (base_ratio or 0)
        print(f"  → BEST {param}={best['value']}: PnL=${best['net_pnl']:,.0f} DD=${best['max_dd_$']:,.0f} P/DD={best['ratio_p_dd']} (Δ={delta:+.2f})")
        best_per_param.append({**best, "delta_pdd": round(delta, 2)})

    print("\n\n=== 1D winners — sorted by P/DD lift vs BASE ===")
    best_per_param.sort(key=lambda r: r["delta_pdd"], reverse=True)
    for r in best_per_param:
        print(f"  {r['param']:<22s} = {str(r['value']):<10s}  P/DD={r['ratio_p_dd']:>5.2f}  Δ={r['delta_pdd']:+5.2f}  "
              f"PnL=${r['net_pnl']:>9,.0f} DD=${r['max_dd_$']:>7,.0f} N={r['trades']}")

    out = Path(__file__).resolve().parents[1] / "logs" / "03_strategy_params.json"
    out.write_text(json.dumps(all_rows, indent=2, default=str))
    print(f"\n[saved] {out}")


if __name__ == "__main__":
    main()
