"""06 — 2-D combos of the most promising params from sweeps 02-04.

Fill BEST_OVERRIDES with the winners from earlier sweeps. We then build
focused 2-D grids around them to discover interactions.

This file is updated after sweep 03 lands.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _campaign as C  # noqa: E402

from scripts.goals._shared.harness import bench  # noqa: E402


TF = "7m"
BASE = dict(C.PREV_WINNER_PARAMS)
BASE["hw_dir_on"] = False  # sweep 02 lever
# Additional overrides filled in after sweep 03 (see logs).
# Example after sweep 03 (placeholder, will edit):
# BASE["signal_length"] = 4
# BASE["sig_extreme"] = 30


# Filled with sweep 03's best per-param values + a couple variants each.
GRIDS = [
    # (name, dict of {param: [values]})
    ("signal_length × sig_extreme", {
        "signal_length": [3, 4, 5],
        "sig_extreme": [25, 30, 35, 40],
    }),
    ("hyper_wave_length × mf_length", {
        "hyper_wave_length": [5, 7, 9],
        "mf_length": [20, 25, 30],
    }),
    ("ssl_len × ssl_mult", {
        "ssl_len": [60, 80, 100],
        "ssl_mult": [0.15, 0.2, 0.25],
    }),
    ("entry_window_bars × max_sl_points", {
        "entry_window_bars": [2, 3, 5],
        "max_sl_points": [150.0, 200.0, 300.0],
    }),
    ("hw_partial_pct × hw_partial_min_rr", {
        "hw_partial_pct": [0.0, 25.0, 50.0],
        "hw_partial_min_rr": [0.0, 0.5, 1.0],
    }),
    ("final_exit_mode × final_exit_pct", {
        "final_exit_mode": ["HMA rapide/SSL → HW", "% du prix d'entrée en profit"],
        "final_exit_pct": [0.05, 0.1, 0.15, 0.2],
    }),
]


def main():
    print(f"=== 06 COMBOS — TF={TF} ===\n")
    print("Base overrides:", {k: v for k, v in BASE.items()
                              if v != C.PREV_WINNER_PARAMS.get(k)})

    rows = []
    rows.append(("REF base", bench(
        f"{'REF base':<45s}",
        strategy_name=C.STRATEGY, symbol=C.SYMBOL, interval=TF,
        start=C.START, end=C.END, strategy_params=BASE,
        initial_equity=C.INITIAL_EQUITY, risk_per_trade=C.DEFAULT_RISK,
        max_contracts=C.MAX_CONTRACTS,
    )))

    for name, grid in GRIDS:
        print(f"\n--- {name} ---")
        keys = list(grid.keys())
        if len(keys) == 1:
            combos = [(v,) for v in grid[keys[0]]]
        else:
            from itertools import product
            combos = list(product(*[grid[k] for k in keys]))
        for combo in combos:
            params = dict(BASE)
            label_parts = []
            for k, v in zip(keys, combo):
                params[k] = v
                label_parts.append(f"{k}={v}")
            label = " ".join(label_parts)
            rows.append((label, bench(
                f"{label:<45s}",
                strategy_name=C.STRATEGY, symbol=C.SYMBOL, interval=TF,
                start=C.START, end=C.END, strategy_params=params,
                initial_equity=C.INITIAL_EQUITY, risk_per_trade=C.DEFAULT_RISK,
                max_contracts=C.MAX_CONTRACTS,
            )))

    print("\n=== TOP 25 by ratio (passing both targets first) ===")
    def sortkey(row):
        s = row[1]
        passes = s["max_dd_$"] < C.TARGET_MAX_DD and s["net_pnl"] >= C.TARGET_PNL_MIN
        return (-int(passes), -(s["net_pnl"] / max(s["max_dd_$"], 1.0)))
    rows.sort(key=sortkey)
    for label, s in rows[:25]:
        ratio = s["net_pnl"] / max(s["max_dd_$"], 1.0)
        mark = "✓" if s["max_dd_$"] < C.TARGET_MAX_DD and s["net_pnl"] >= C.TARGET_PNL_MIN else " "
        print(f"  {mark} {label:<45s}  ratio={ratio:>6.2f}  "
              f"PnL=${s['net_pnl']:>9,.0f}  DD=${s['max_dd_$']:>6,.0f}  "
              f"PF={s['profit_factor']}  N={s['trades']}")


if __name__ == "__main__":
    main()
