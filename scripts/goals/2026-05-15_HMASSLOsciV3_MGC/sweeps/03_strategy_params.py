"""Sweep 03 — Strategy core params on 7m for HMASSLOsciV3 / MGC.

Starting from the best 02-baseline (hw_range_on=True), sweep 1-D on each
hyperparameter to find sensitivities and a refined starting config.

Base config = defaults + {hw_range_on=True}.
"""

from __future__ import annotations

import json
from pathlib import Path

from _campaign import DEFAULT_RISK, END, INITIAL_EQUITY, MAX_CONTRACTS, START, STRATEGY, SYMBOL

from scripts.goals._shared.harness import bench

BEST_TF = "7m"

BASE = {"hw_range_on": True}

SWEEPS = {
    "hw_range": [5.0, 8.0, 10.0, 12.0, 15.0, 20.0],
    "hma_pol_bars": [0, 2, 3, 4, 5, 6, 8, 12],
    "hyper_wave_length": [3, 5, 7, 9],
    "signal_length": [2, 3, 4, 5],
    "sig_extreme": [15.0, 20.0, 25.0, 30.0, 35.0, 40.0],
    "hw_extreme": [10.0, 15.0, 20.0, 25.0, 30.0],
    "mf_length": [20, 25, 35, 45, 55],
    "mf_smooth": [3, 4, 6, 8, 10],
    "ssl_len": [40, 60, 80, 100],
    "ssl_mult": [0.1, 0.15, 0.2, 0.25, 0.3],
    "entry_window_bars": [2, 3, 4, 5, 6, 8],
    "max_sl_points": [50.0, 100.0, 150.0, 200.0, 300.0],
    "amp_mult": [1.5, 2.0, 2.5, 3.0],
    "hma1_len": [9, 13, 17, 21],
    "hma2_len": [17, 21, 25, 34],
    "ema_len": [9, 11, 13, 15],
}


def main():
    print(f"=== Sweep 03: strategy params 1D — {STRATEGY} / {SYMBOL} ({BEST_TF}) ===")
    print(f"    BASE overrides: {BASE}")
    print()
    all_rows = []
    for param, values in SWEEPS.items():
        print(f"--- {param} ---")
        rows = []
        for v in values:
            overrides = dict(BASE)
            overrides[param] = v
            s = bench(
                label=f"{param}={v}",
                strategy_name=STRATEGY,
                symbol=SYMBOL,
                interval=BEST_TF,
                start=START,
                end=END,
                initial_equity=INITIAL_EQUITY,
                risk_per_trade=DEFAULT_RISK,
                max_contracts=MAX_CONTRACTS,
                strategy_params=overrides,
            )
            s["param"] = param
            s["value"] = v
            s["ratio_p_dd"] = round(s["net_pnl"] / s["max_dd_$"], 2) if s["max_dd_$"] > 0 else None
            rows.append(s)
        rows.sort(key=lambda r: (r["ratio_p_dd"] or -999), reverse=True)
        print(f"  Best for {param}: {rows[0]['param']}={rows[0]['value']}  "
              f"P/DD={rows[0]['ratio_p_dd']}  PnL=${rows[0]['net_pnl']:,.0f}  "
              f"DD=${rows[0]['max_dd_$']:,.0f}  N={rows[0]['trades']}")
        all_rows.extend(rows)
        print()

    out = Path(__file__).resolve().parents[1] / "logs" / "03_strategy_params.json"
    out.write_text(json.dumps(all_rows, indent=2, default=str))
    print(f"[saved] {out}")


if __name__ == "__main__":
    main()
