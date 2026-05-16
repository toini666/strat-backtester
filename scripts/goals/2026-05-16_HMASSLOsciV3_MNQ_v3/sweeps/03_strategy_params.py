"""03 — Strategy params 1-D from improved baseline.

Baseline = v2_winner params + hw_dir_on=False (from sweep 02 winner).

We 1-D sweep each parameter holding others at baseline. Goal: identify levers
that further reduce DD (currently $2,825 — slightly above target $2,500) or
push PnL up while keeping DD trend favorable.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _campaign as C  # noqa: E402

from scripts.goals._shared.harness import bench  # noqa: E402


TF = "7m"
BASE = dict(C.PREV_WINNER_PARAMS)
BASE["hw_dir_on"] = False  # sweep 02 winner

SWEEPS: dict[str, list] = {
    "signal_length":      [2, 3, 4, 5, 6],
    "sig_extreme":        [20, 25, 30, 35, 40],
    "hyper_wave_length":  [3, 5, 7, 9, 11],
    "mf_length":          [15, 20, 25, 30, 35, 45],
    "mf_smooth":          [3, 4, 5, 6, 8],
    "ssl_len":            [40, 60, 80, 100, 120],
    "ssl_mult":           [0.1, 0.15, 0.2, 0.25, 0.3],
    "entry_window_bars":  [1, 2, 3, 5, 8],
    "ema_len":            [9, 13, 17, 21],
    "hma1_len":           [9, 13, 17, 21],
    "hma2_len":           [13, 17, 21, 25, 34],
    "amp_mult":           [1.5, 2.0, 2.5, 3.0],
    "hma_pol_bars":       [0, 2, 3, 5],
    "max_sl_points":      [100.0, 150.0, 200.0, 250.0, 300.0],
    "max_candle_pct":     [0.5, 0.7, 0.9, 1.0],
    "hw_extreme":         [15.0, 20.0, 25.0, 30.0],
    "cooldown_bars":      [0, 1, 2, 3],
    "tick_buffer":        [0, 1, 2, 3],
    "hw_partial_pct":     [0.0, 25.0, 50.0, 75.0],
    "hw_partial_min_rr":  [0.0, 0.5, 1.0],
    "final_exit_pct":     [0.05, 0.1, 0.15, 0.2, 0.3],
}


def main():
    print(f"=== 03 STRATEGY PARAMS 1-D — TF={TF} ===")
    print(f"Baseline = v2_winner + hw_dir_on=False")
    print()

    ref = bench(
        f"{'REF base':<35s}",
        strategy_name=C.STRATEGY, symbol=C.SYMBOL, interval=TF,
        start=C.START, end=C.END, strategy_params=BASE,
        initial_equity=C.INITIAL_EQUITY, risk_per_trade=C.DEFAULT_RISK,
        max_contracts=C.MAX_CONTRACTS,
    )

    all_rows = [("REF base", ref)]
    best_per_param = {}
    for param, values in SWEEPS.items():
        print(f"\n--- {param} ---")
        param_rows = []
        for v in values:
            params = dict(BASE)
            params[param] = v
            label = f"{param}={v}"
            s = bench(
                f"{label:<35s}",
                strategy_name=C.STRATEGY, symbol=C.SYMBOL, interval=TF,
                start=C.START, end=C.END, strategy_params=params,
                initial_equity=C.INITIAL_EQUITY, risk_per_trade=C.DEFAULT_RISK,
                max_contracts=C.MAX_CONTRACTS,
            )
            param_rows.append((label, v, s))
            all_rows.append((label, s))
        param_rows.sort(key=lambda x: x[2]["net_pnl"] / max(x[2]["max_dd_$"], 1.0),
                        reverse=True)
        best_per_param[param] = param_rows[0]

    print("\n=== BEST per-param by ratio ===")
    for param, (label, v, s) in best_per_param.items():
        ratio = s["net_pnl"] / max(s["max_dd_$"], 1.0)
        mark = "✓" if s["max_dd_$"] < C.TARGET_MAX_DD and s["net_pnl"] >= C.TARGET_PNL_MIN else " "
        print(f"  {mark} {label:<35s}  ratio={ratio:>6.2f}  "
              f"PnL=${s['net_pnl']:>9,.0f}  DD=${s['max_dd_$']:>6,.0f}  "
              f"PF={s['profit_factor']}  N={s['trades']}")

    print("\n=== TOP 20 (all combos) ===")
    all_rows.sort(key=lambda x: x[1]["net_pnl"] / max(x[1]["max_dd_$"], 1.0), reverse=True)
    for label, s in all_rows[:20]:
        ratio = s["net_pnl"] / max(s["max_dd_$"], 1.0)
        mark = "✓" if s["max_dd_$"] < C.TARGET_MAX_DD and s["net_pnl"] >= C.TARGET_PNL_MIN else " "
        print(f"  {mark} {label:<35s}  ratio={ratio:>6.2f}  "
              f"PnL=${s['net_pnl']:>9,.0f}  DD=${s['max_dd_$']:>6,.0f}  "
              f"PF={s['profit_factor']}  N={s['trades']}")


if __name__ == "__main__":
    main()
