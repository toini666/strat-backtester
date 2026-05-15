"""02 — Filter activation.

Sur le meilleur TF (M7, ratio 1.74). On toggle un par un les filtres optionnels
exposés par HMASSLOsciV3 :
  - cloud_on (default False)            — filtre MFI cloud
  - cloud_zero_on (default False)       — MFI > 0 / < 0 strict
  - delta_ext_on (default False)        — delta contrarian extrême
  - hw_range_on (default False)         — HW out of range
  - hma_pol_bars (default 3)            — testé à 0 (off)
  - one_trade_per_entry_window (def True) — testé à False
  - signal_candle_sl_on (default False) — signal candle SL gate

Garde ceux qui améliorent PF ou réduisent DD sans tuer le volume.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _campaign as C  # noqa: E402

from scripts.goals._shared.harness import bench  # noqa: E402

TF = "7m"


def main():
    print(f"=== 02 FILTER ACTIVATION — {C.STRATEGY} {C.SYMBOL} {TF} ===\n")

    base_params = None  # native defaults
    base = bench("BASE (defaults)", strategy_name=C.STRATEGY, symbol=C.SYMBOL,
                 interval=TF, start=C.START, end=C.END,
                 strategy_params=base_params, initial_equity=C.INITIAL_EQUITY,
                 risk_per_trade=C.DEFAULT_RISK, max_contracts=C.MAX_CONTRACTS)

    toggles = [
        ("cloud_on=True", {"cloud_on": True}),
        ("cloud_zero_on=True", {"cloud_zero_on": True}),
        ("delta_ext_on=True", {"delta_ext_on": True}),
        ("hw_range_on=True", {"hw_range_on": True}),
        ("hma_pol_bars=0 (off)", {"hma_pol_bars": 0}),
        ("hma_pol_bars=5", {"hma_pol_bars": 5}),
        ("one_trade_per_entry_window=False", {"one_trade_per_entry_window": False}),
        ("signal_candle_sl_on=True", {"signal_candle_sl_on": True}),
        ("hw_dir_on=False", {"hw_dir_on": False}),
        ("hw_extreme_on=False", {"hw_extreme_on": False}),
        ("sig_extreme_on=False", {"sig_extreme_on": False}),
        ("delta_on=False", {"delta_on": False}),
        # combos likely to help
        ("cloud_on+single_trade_off",
         {"cloud_on": True, "one_trade_per_entry_window": False}),
        ("cloud_on+hma_pol_bars=0",
         {"cloud_on": True, "hma_pol_bars": 0}),
    ]

    results = [("BASE", base)]
    for label, overrides in toggles:
        s = bench(label, strategy_name=C.STRATEGY, symbol=C.SYMBOL,
                  interval=TF, start=C.START, end=C.END,
                  strategy_params=overrides, initial_equity=C.INITIAL_EQUITY,
                  risk_per_trade=C.DEFAULT_RISK, max_contracts=C.MAX_CONTRACTS)
        results.append((label, s))

    print("\n--- Ranked by Profit/DD ratio ---")
    ranked = sorted(results,
                    key=lambda x: (x[1]["net_pnl"] / max(x[1]["max_dd_$"], 1.0)),
                    reverse=True)
    for label, s in ranked:
        ratio = s["net_pnl"] / max(s["max_dd_$"], 1.0)
        print(f"  {label:<40s} ratio={ratio:>6.2f}  PnL=${s['net_pnl']:>9,.0f}  "
              f"DD=${s['max_dd_$']:>6,.0f}  PF={s['profit_factor']}  N={s['trades']}")


if __name__ == "__main__":
    main()
