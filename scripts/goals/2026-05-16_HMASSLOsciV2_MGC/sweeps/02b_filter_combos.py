"""Sweep 02b — Filter combos starting from delta_ext_on=True base."""

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
BASE = {"delta_ext_on": True}

# Additive toggles on top of delta_ext_on=True
ADDITIVE = [
    {"cloud_zero_on": True},
    {"cloud_on": True},
    {"delta_on": True},
    {"sig_extreme_on": True},
    {"block_loss_exit_before_partial": False},
    {"hw_dir_on": True},
    # combos of top-2
    {"cloud_zero_on": True, "cloud_on": True},
    {"cloud_zero_on": True, "block_loss_exit_before_partial": False},
    {"cloud_zero_on": True, "delta_on": True},
    {"cloud_zero_on": True, "sig_extreme_on": True},
    {"cloud_zero_on": True, "hw_dir_on": True},
]


def main():
    print(f"=== Sweep 02b: filter combos on base delta_ext_on=True — {TF} ===")
    print()

    # Base
    base = bench(
        label="base: delta_ext_on=True",
        strategy_name=STRATEGY, symbol=SYMBOL, interval=TF,
        start=START, end=END,
        strategy_params=BASE,
        initial_equity=INITIAL_EQUITY, risk_per_trade=DEFAULT_RISK,
        max_contracts=MAX_CONTRACTS,
    )
    base["ratio_p_dd"] = round(base["net_pnl"] / base["max_dd_$"], 2) if base["max_dd_$"] > 0 else None
    rows = [{"label": "base", **base, "delta_pnl": 0, "delta_dd": 0}]

    print()
    for combo in ADDITIVE:
        params = {**BASE, **combo}
        label = "+" + ",".join(f"{k}={v}" for k, v in combo.items())
        s = bench(
            label=label,
            strategy_name=STRATEGY, symbol=SYMBOL, interval=TF,
            start=START, end=END,
            strategy_params=params,
            initial_equity=INITIAL_EQUITY, risk_per_trade=DEFAULT_RISK,
            max_contracts=MAX_CONTRACTS,
        )
        s["ratio_p_dd"] = round(s["net_pnl"] / s["max_dd_$"], 2) if s["max_dd_$"] > 0 else None
        rows.append({
            "label": label,
            "delta_pnl": round(s["net_pnl"] - base["net_pnl"], 2),
            "delta_dd": round(s["max_dd_$"] - base["max_dd_$"], 2),
            **s,
        })

    print()
    print("=== Combo deltas (sorted by P/DD ratio) ===")
    rows_sorted = sorted(rows, key=lambda r: r["ratio_p_dd"] or -999, reverse=True)
    for r in rows_sorted:
        print(f"  {r['label']:<60s} PnL=${r['net_pnl']:>9,.0f} DD=${r['max_dd_$']:>6,.0f} "
              f"N={r['trades']:>4} WR={r['win_rate']}% P/DD={r['ratio_p_dd']} "
              f"(ΔPnL=${r['delta_pnl']:>+8,.0f} ΔDD=${r['delta_dd']:>+7,.0f})")

    out = Path(__file__).resolve().parents[1] / "logs" / "02b_filter_combos.json"
    out.write_text(json.dumps(rows, indent=2, default=str))
    print(f"\n[saved] {out}")


if __name__ == "__main__":
    main()
