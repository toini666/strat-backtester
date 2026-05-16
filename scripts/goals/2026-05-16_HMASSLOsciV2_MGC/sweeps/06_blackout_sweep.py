"""Sweep 06 — Targeted blackouts based on hour analysis.

Toxic hours from sweep 05: H=11, H=14, H=10, H=06, H=16
(H=23 is already covered by UI default 22:00-23:59)
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


def _windows(*hours):
    return [{"start_hour": h, "start_minute": 0,
             "end_hour": h + 1, "end_minute": 0} for h in hours]


# Each candidate is a tuple of hours to blackout
COMBOS = [
    [],              # baseline (no blackout)
    [11],
    [14],
    [10],
    [6],
    [16],
    [11, 14],
    [11, 10],
    [11, 14, 10],
    [11, 14, 10, 6],
    [11, 14, 10, 16],
    [11, 14, 10, 6, 16],
    [11, 14, 6],
    [11, 10, 6],
    [11, 14, 10, 6, 16],
    # also try smaller windows
    [11, 6],
]


def main():
    print(f"=== Sweep 06 — targeted blackouts — {STRATEGY} / {SYMBOL} / {TF} ===")
    print(f"    BASE_V2 = {BASE_V2}")
    print()

    rows = []
    for hours in COMBOS:
        if hours:
            label = f"BO[{','.join(str(h) for h in hours)}]"
            es = make_engine_settings(STRATEGY, extra_active_windows=_windows(*hours))
        else:
            label = "baseline"
            es = make_engine_settings(STRATEGY)
        s = bench(
            label=label,
            strategy_name=STRATEGY, symbol=SYMBOL, interval=TF,
            start=START, end=END, strategy_params=BASE_V2,
            initial_equity=INITIAL_EQUITY, risk_per_trade=DEFAULT_RISK,
            max_contracts=MAX_CONTRACTS,
            engine_settings=es,
        )
        s["ratio_p_dd"] = round(s["net_pnl"] / s["max_dd_$"], 2) if s["max_dd_$"] > 0 else None
        s["label"] = label
        s["hours"] = hours
        rows.append(s)

    print("\n=== TOP rankings ===")
    rows_sorted = sorted(rows, key=lambda r: r["ratio_p_dd"] or -999, reverse=True)
    for r in rows_sorted:
        print(f"  {r['label']:<35s} PnL=${r['net_pnl']:>9,.0f} DD=${r['max_dd_$']:>6,.0f} "
              f"N={r['trades']:>4} WR={r['win_rate']}% PF={r['profit_factor']} P/DD={r['ratio_p_dd']}")

    out = Path(__file__).resolve().parents[1] / "logs" / "06_blackout_sweep.json"
    out.write_text(json.dumps(rows, indent=2, default=str))
    print(f"\n[saved] {out}")


if __name__ == "__main__":
    main()
