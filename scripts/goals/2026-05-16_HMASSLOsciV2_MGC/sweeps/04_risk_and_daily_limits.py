"""Sweep 04 — Risk per trade + Daily win/loss limits on BASE_V2.

BASE_V2: best strategy params from sweep 03b.
- Step A: risk_per_trade grid
- Step B: daily limits in intra_bar mode (preferred)
- Step C: daily limits in after_close mode (fallback)
"""

from __future__ import annotations

import json
from pathlib import Path

from _campaign import (
    END,
    INITIAL_EQUITY,
    MAX_CONTRACTS,
    START,
    STRATEGY,
    SYMBOL,
)

from scripts.goals._shared.engine_settings import make_engine_settings
from scripts.goals._shared.harness import bench


TF = "7m"
BASE_V2 = {
    "delta_ext_on": True,
    "cloud_zero_on": True,
    "sig_extreme_on": True,
    "mf_smooth": 3,
    "cooldown_bars": 5,
    "max_candle_pct": 0.7,
}

# Step A — risk_per_trade
RISKS = [0.001, 0.002, 0.003, 0.004, 0.005, 0.006, 0.007, 0.0075, 0.008, 0.01, 0.012, 0.015, 0.02]

# Step B/C — daily limits (win/loss)
# Will be tested at the best (or default) risk
DAILY_GRID = [
    (None, None),                    # no limit
    (250.0, 350.0),
    (500.0, 700.0),
    (300.0, 500.0),
    (400.0, 600.0),
    (200.0, 400.0),
    (250.0, 250.0),
    (500.0, 500.0),
    (750.0, 1000.0),
    (1000.0, 1500.0),
]


def main():
    print(f"=== Sweep 04 — risk_per_trade + daily limits — {STRATEGY} / {SYMBOL} / {TF} ===")
    print(f"    BASE_V2 = {BASE_V2}")
    print()

    rows = []

    print("--- A. risk_per_trade sweep ---")
    for r in RISKS:
        s = bench(
            label=f"risk={r}",
            strategy_name=STRATEGY, symbol=SYMBOL, interval=TF,
            start=START, end=END, strategy_params=BASE_V2,
            initial_equity=INITIAL_EQUITY, risk_per_trade=r,
            max_contracts=MAX_CONTRACTS,
        )
        s["ratio_p_dd"] = round(s["net_pnl"] / s["max_dd_$"], 2) if s["max_dd_$"] > 0 else None
        s["label"] = f"risk={r}"
        s["risk"] = r
        rows.append(s)

    # Pick best risk by P/DD that also has PnL > 0
    valid = [r for r in rows if r["net_pnl"] > 0]
    best_risk_row = max(valid, key=lambda r: r["ratio_p_dd"] or -999)
    best_risk = best_risk_row["risk"]
    print(f"\n  → BEST risk by P/DD: {best_risk} → {best_risk_row['ratio_p_dd']} "
          f"(PnL=${best_risk_row['net_pnl']:,.0f} DD=${best_risk_row['max_dd_$']:,.0f})")

    # Also pick a risk close to target DD (≤ 2500), highest PnL
    close_dd = [r for r in rows if r["max_dd_$"] <= 2500]
    if close_dd:
        cand = max(close_dd, key=lambda r: r["net_pnl"])
        print(f"  → BEST risk with DD<2500: {cand['risk']} → PnL=${cand['net_pnl']:,.0f} DD=${cand['max_dd_$']:,.0f}")

    print("\n--- B. daily limits — intra_bar mode (at risk=0.01 baseline) ---")
    for dwl, dll in DAILY_GRID:
        es = make_engine_settings(
            STRATEGY,
            daily_win_limit=dwl, daily_loss_limit=dll,
            daily_limit_mode="intra_bar",
        )
        s = bench(
            label=f"intra_bar/win={dwl}/loss={dll}",
            strategy_name=STRATEGY, symbol=SYMBOL, interval=TF,
            start=START, end=END, strategy_params=BASE_V2,
            initial_equity=INITIAL_EQUITY, risk_per_trade=0.01,
            max_contracts=MAX_CONTRACTS,
            engine_settings=es,
        )
        s["ratio_p_dd"] = round(s["net_pnl"] / s["max_dd_$"], 2) if s["max_dd_$"] > 0 else None
        s["label"] = f"intra_bar/win={dwl}/loss={dll}"
        s["mode"], s["win_cap"], s["loss_cap"] = "intra_bar", dwl, dll
        rows.append(s)

    print("\n--- C. daily limits — after_close mode (at risk=0.01 baseline) ---")
    for dwl, dll in DAILY_GRID:
        es = make_engine_settings(
            STRATEGY,
            daily_win_limit=dwl, daily_loss_limit=dll,
            daily_limit_mode="after_close",
        )
        s = bench(
            label=f"after_close/win={dwl}/loss={dll}",
            strategy_name=STRATEGY, symbol=SYMBOL, interval=TF,
            start=START, end=END, strategy_params=BASE_V2,
            initial_equity=INITIAL_EQUITY, risk_per_trade=0.01,
            max_contracts=MAX_CONTRACTS,
            engine_settings=es,
        )
        s["ratio_p_dd"] = round(s["net_pnl"] / s["max_dd_$"], 2) if s["max_dd_$"] > 0 else None
        s["label"] = f"after_close/win={dwl}/loss={dll}"
        s["mode"], s["win_cap"], s["loss_cap"] = "after_close", dwl, dll
        rows.append(s)

    print("\n=== TOP 15 overall (P/DD ratio) ===")
    rows_sorted = sorted(rows, key=lambda r: r["ratio_p_dd"] or -999, reverse=True)
    for r in rows_sorted[:20]:
        print(f"  {r['label']:<55s} PnL=${r['net_pnl']:>9,.0f} DD=${r['max_dd_$']:>6,.0f} "
              f"N={r['trades']:>4} P/DD={r['ratio_p_dd']}")

    out = Path(__file__).resolve().parents[1] / "logs" / "04_risk_and_daily_limits.json"
    out.write_text(json.dumps(rows, indent=2, default=str))
    print(f"\n[saved] {out}")


if __name__ == "__main__":
    main()
