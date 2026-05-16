"""Sweep 03b — Combo test of 1D winners + fine-grained around mf_smooth.

Tests whether 1D winners are additive when stacked, and fine-tunes mf_smooth.
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

# Top 1D winners to combine
COMBOS = [
    # singles for reference
    {"mf_smooth": 3},
    {"cooldown_bars": 5},
    {"ssl_mult": 0.1},
    {"max_candle_pct": 0.7},
    # additive doubles
    {"mf_smooth": 3, "cooldown_bars": 5},
    {"mf_smooth": 3, "ssl_mult": 0.1},
    {"mf_smooth": 3, "max_candle_pct": 0.7},
    {"cooldown_bars": 5, "ssl_mult": 0.1},
    {"cooldown_bars": 5, "max_candle_pct": 0.7},
    {"ssl_mult": 0.1, "max_candle_pct": 0.7},
    # triple
    {"mf_smooth": 3, "cooldown_bars": 5, "ssl_mult": 0.1},
    {"mf_smooth": 3, "cooldown_bars": 5, "max_candle_pct": 0.7},
    {"mf_smooth": 3, "ssl_mult": 0.1, "max_candle_pct": 0.7},
    {"cooldown_bars": 5, "ssl_mult": 0.1, "max_candle_pct": 0.7},
    # quad
    {"mf_smooth": 3, "cooldown_bars": 5, "ssl_mult": 0.1, "max_candle_pct": 0.7},
]

# Fine-grained mf_smooth (default 6, best=3)
FINE_MF_SMOOTH = [1, 2, 3, 4, 5]
# Fine-grained cooldown (best=5)
FINE_COOLDOWN = [4, 5, 6, 7, 10]


def main():
    print(f"=== Sweep 03b: combo + fine-grained — {TF} ===")
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
    print()

    rows = [{"label": "BASE", **base}]

    print("--- COMBOS ---")
    for combo in COMBOS:
        params = {**BASE, **combo}
        label = "+".join(f"{k}={v}" for k, v in combo.items())
        s = bench(
            label=label,
            strategy_name=STRATEGY, symbol=SYMBOL, interval=TF,
            start=START, end=END, strategy_params=params,
            initial_equity=INITIAL_EQUITY, risk_per_trade=DEFAULT_RISK,
            max_contracts=MAX_CONTRACTS,
        )
        s["ratio_p_dd"] = round(s["net_pnl"] / s["max_dd_$"], 2) if s["max_dd_$"] > 0 else None
        s["label"] = label
        rows.append(s)

    print("\n--- FINE mf_smooth ---")
    for v in FINE_MF_SMOOTH:
        params = {**BASE, "mf_smooth": v}
        s = bench(
            label=f"mf_smooth={v}",
            strategy_name=STRATEGY, symbol=SYMBOL, interval=TF,
            start=START, end=END, strategy_params=params,
            initial_equity=INITIAL_EQUITY, risk_per_trade=DEFAULT_RISK,
            max_contracts=MAX_CONTRACTS,
        )
        s["ratio_p_dd"] = round(s["net_pnl"] / s["max_dd_$"], 2) if s["max_dd_$"] > 0 else None
        s["label"] = f"mf_smooth={v}"
        rows.append(s)

    print("\n--- FINE cooldown ---")
    for v in FINE_COOLDOWN:
        params = {**BASE, "cooldown_bars": v}
        s = bench(
            label=f"cooldown_bars={v}",
            strategy_name=STRATEGY, symbol=SYMBOL, interval=TF,
            start=START, end=END, strategy_params=params,
            initial_equity=INITIAL_EQUITY, risk_per_trade=DEFAULT_RISK,
            max_contracts=MAX_CONTRACTS,
        )
        s["ratio_p_dd"] = round(s["net_pnl"] / s["max_dd_$"], 2) if s["max_dd_$"] > 0 else None
        s["label"] = f"cooldown_bars={v}"
        rows.append(s)

    print("\n=== TOP 10 by Profit/DD ratio ===")
    rows_sorted = sorted(rows, key=lambda r: r["ratio_p_dd"] or -999, reverse=True)
    for r in rows_sorted[:15]:
        print(f"  {r['label']:<70s} PnL=${r['net_pnl']:>9,.0f} DD=${r['max_dd_$']:>6,.0f} "
              f"N={r['trades']:>4} WR={r['win_rate']}% PF={r['profit_factor']} P/DD={r['ratio_p_dd']}")

    out = Path(__file__).resolve().parents[1] / "logs" / "03b_combo_test.json"
    out.write_text(json.dumps(rows, indent=2, default=str))
    print(f"\n[saved] {out}")


if __name__ == "__main__":
    main()
