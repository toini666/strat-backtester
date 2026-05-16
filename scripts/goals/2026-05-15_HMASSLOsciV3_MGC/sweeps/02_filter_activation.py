"""Sweep 02 — Filter activation on best TF (7m) for HMASSLOsciV3 / MGC.

Toggle each oscillator filter independently to test impact on PF and DD.
Strategy default already has: hw_dir_on, hw_extreme_on, sig_extreme_on, delta_on = True
                              cloud_on, hw_range_on, cloud_zero_on, delta_ext_on = False
                              one_trade_per_entry_window = True
                              hma_pol_bars = 3
"""

from __future__ import annotations

import json
from pathlib import Path

from _campaign import DEFAULT_RISK, END, INITIAL_EQUITY, MAX_CONTRACTS, START, STRATEGY, SYMBOL

from scripts.goals._shared.harness import bench

BEST_TF = "7m"


VARIANTS = [
    ("baseline (defaults)", {}),
    ("cloud_on=True", {"cloud_on": True}),
    ("hw_range_on=True", {"hw_range_on": True}),
    ("cloud_zero_on=True", {"cloud_zero_on": True}),
    ("delta_ext_on=True", {"delta_ext_on": True}),
    ("hw_dir_on=False", {"hw_dir_on": False}),
    ("hw_extreme_on=False", {"hw_extreme_on": False}),
    ("sig_extreme_on=False", {"sig_extreme_on": False}),
    ("delta_on=False", {"delta_on": False}),
    ("one_trade_per_entry_window=False", {"one_trade_per_entry_window": False}),
    ("hma_pol_bars=0", {"hma_pol_bars": 0}),
    ("hma_pol_bars=5", {"hma_pol_bars": 5}),
    # Combinations of "filter additions"
    ("cloud_on + hma_pol_bars=0", {"cloud_on": True, "hma_pol_bars": 0}),
    ("cloud_on + delta_ext_on", {"cloud_on": True, "delta_ext_on": True}),
    ("cloud_on + cloud_zero_on", {"cloud_on": True, "cloud_zero_on": True}),
]


def main():
    print(f"=== Sweep 02: filter activation — {STRATEGY} / {SYMBOL} ({BEST_TF}) ===")
    rows = []
    for label, overrides in VARIANTS:
        s = bench(
            label=label,
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
        s["overrides"] = overrides
        s["ratio_p_dd"] = round(s["net_pnl"] / s["max_dd_$"], 2) if s["max_dd_$"] > 0 else None
        rows.append(s)

    print()
    print("=== Ranking by Profit/DD ratio ===")
    rows.sort(key=lambda r: (r["ratio_p_dd"] or -999), reverse=True)
    for r in rows:
        print(f"  P/DD={r['ratio_p_dd']:>6}  PnL=${r['net_pnl']:>9,.0f}  DD=${r['max_dd_$']:>6,.0f}  "
              f"PF={r['profit_factor']}  N={r['trades']:>4}  WR={r['win_rate']}%  -- {r['label']}")

    out = Path(__file__).resolve().parents[1] / "logs" / "02_filter_activation.json"
    out.write_text(json.dumps(rows, indent=2, default=str))
    print(f"\n[saved] {out}")


if __name__ == "__main__":
    main()
