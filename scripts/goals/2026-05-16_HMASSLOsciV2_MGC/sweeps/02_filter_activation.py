"""Sweep 02 — Filter activation for HMASSLOsciV2.

Run on M7 (best baseline volume + better P/DD than shorter TFs).
Toggle each boolean filter individually on top of default_params and report deltas.
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

# (param, value_to_test, default_value)
# Filters that default to FALSE → test True
# Filters that default to TRUE  → test False
TOGGLES = [
    # Default False — test True
    ("hw_dir_on", True, False),
    ("hw_extreme_on", True, False),
    ("sig_extreme_on", True, False),
    ("hw_range_on", True, False),
    ("cloud_on", True, False),
    ("delta_on", True, False),
    ("cloud_zero_on", True, False),
    ("delta_ext_on", True, False),
    # Default True — test False
    ("hma_side_on", False, True),
    ("signal_candle_sl_on", False, True),
    ("block_loss_exit_before_partial", False, True),
]


def main():
    print(f"=== Sweep 02: filter activation — {STRATEGY} / {SYMBOL} / {TF} ===")
    print()

    # Baseline reference (no overrides)
    baseline = bench(
        label=f"baseline-{TF}",
        strategy_name=STRATEGY, symbol=SYMBOL, interval=TF,
        start=START, end=END,
        initial_equity=INITIAL_EQUITY, risk_per_trade=DEFAULT_RISK,
        max_contracts=MAX_CONTRACTS,
    )
    baseline["ratio_p_dd"] = round(baseline["net_pnl"] / baseline["max_dd_$"], 2) if baseline["max_dd_$"] > 0 else None
    rows = [{"label": "baseline", "delta_pnl": 0, "delta_dd": 0, **baseline}]

    print()
    for param, val, default in TOGGLES:
        params = {param: val}
        s = bench(
            label=f"{param}={val}",
            strategy_name=STRATEGY, symbol=SYMBOL, interval=TF,
            start=START, end=END,
            strategy_params=params,
            initial_equity=INITIAL_EQUITY, risk_per_trade=DEFAULT_RISK,
            max_contracts=MAX_CONTRACTS,
        )
        s["ratio_p_dd"] = round(s["net_pnl"] / s["max_dd_$"], 2) if s["max_dd_$"] > 0 else None
        rows.append({
            "label": f"{param}={val}",
            "delta_pnl": round(s["net_pnl"] - baseline["net_pnl"], 2),
            "delta_dd": round(s["max_dd_$"] - baseline["max_dd_$"], 2),
            **s,
        })

    print()
    print("=== Filter activation deltas (sorted by Profit/DD ratio improvement) ===")
    rows_sorted = sorted(rows, key=lambda r: r["ratio_p_dd"] or -999, reverse=True)
    for r in rows_sorted:
        print(f"  {r['label']:<35s} PnL=${r['net_pnl']:>9,.0f}  DD=${r['max_dd_$']:>6,.0f}  "
              f"N={r['trades']:>4}  WR={r['win_rate']}%  P/DD={r['ratio_p_dd']}  "
              f"(ΔPnL=${r['delta_pnl']:>+9,.0f} ΔDD=${r['delta_dd']:>+7,.0f})")

    out = Path(__file__).resolve().parents[1] / "logs" / "02_filter_activation.json"
    out.write_text(json.dumps(rows, indent=2, default=str))
    print(f"\n[saved] {out}")


if __name__ == "__main__":
    main()
