"""Sweep 07b — Final combos exploring the best P/DD configurations.

Tests:
- Combinations of tick_buffer=1 with other deltas
- BO[11,14,10] (3-hour, less overfit per advisor)
- BO[11,14,10] + 10m TF pivot (advisor's last lever)
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


BASE_V2 = {
    "delta_ext_on": True,
    "cloud_zero_on": True,
    "sig_extreme_on": True,
    "mf_smooth": 3,
    "cooldown_bars": 5,
    "max_candle_pct": 0.7,
}


def _es(hours):
    return make_engine_settings(
        STRATEGY,
        extra_active_windows=[
            {"start_hour": h, "start_minute": 0, "end_hour": h + 1, "end_minute": 0}
            for h in hours
        ],
    )


CASES = [
    # (label, tf, params_overrides, blackout_hours, risk)
    # === Best config from sweep 07 ===
    ("REF_BO[11,14,10,6]+tick_buffer=1", "7m", {"tick_buffer": 1}, [11, 14, 10, 6], 0.01),
    # === BO 3-hour variants (robust per advisor) ===
    ("BO[11,14,10]+tick_buffer=1", "7m", {"tick_buffer": 1}, [11, 14, 10], 0.01),
    ("BO[11,14,10] (default tick_buffer)", "7m", {}, [11, 14, 10], 0.01),
    # === tick_buffer combos ===
    ("BO[11,14,10,6]+tick_buffer=1+max_candle_pct=0.5", "7m",
     {"tick_buffer": 1, "max_candle_pct": 0.5}, [11, 14, 10, 6], 0.01),
    ("BO[11,14,10,6]+tick_buffer=1+exit_mode=inversion_hma", "7m",
     {"tick_buffer": 1, "exit_mode": "inversion_hma"}, [11, 14, 10, 6], 0.01),
    ("BO[11,14,10]+tick_buffer=1+max_candle_pct=0.5", "7m",
     {"tick_buffer": 1, "max_candle_pct": 0.5}, [11, 14, 10], 0.01),
    # === Risk variations on tick_buffer=1 ===
    ("risk=0.012+tick_buffer=1+BO[11,14,10,6]", "7m", {"tick_buffer": 1}, [11, 14, 10, 6], 0.012),
    ("risk=0.008+tick_buffer=1+BO[11,14,10,6]", "7m", {"tick_buffer": 1}, [11, 14, 10, 6], 0.008),
    ("risk=0.009+tick_buffer=1+BO[11,14,10,6]", "7m", {"tick_buffer": 1}, [11, 14, 10, 6], 0.009),
    ("risk=0.011+tick_buffer=1+BO[11,14,10,6]", "7m", {"tick_buffer": 1}, [11, 14, 10, 6], 0.011),
    # === 10m pivot (advisor's lever) ===
    ("10m+BO[11,14,10]", "10m", {}, [11, 14, 10], 0.01),
    ("10m+BO[11,14,10,6]", "10m", {}, [11, 14, 10, 6], 0.01),
    ("10m+BO[11,14,10,6]+tick_buffer=1", "10m", {"tick_buffer": 1}, [11, 14, 10, 6], 0.01),
    # === Triple tick_buffer combo at lower risk (target DD<2500) ===
    ("risk=0.003+tick_buffer=1+BO[11,14,10,6]", "7m", {"tick_buffer": 1}, [11, 14, 10, 6], 0.003),
    ("risk=0.004+tick_buffer=1+BO[11,14,10,6]", "7m", {"tick_buffer": 1}, [11, 14, 10, 6], 0.004),
    ("risk=0.005+tick_buffer=1+BO[11,14,10,6]", "7m", {"tick_buffer": 1}, [11, 14, 10, 6], 0.005),
    ("risk=0.006+tick_buffer=1+BO[11,14,10,6]", "7m", {"tick_buffer": 1}, [11, 14, 10, 6], 0.006),
    ("risk=0.007+tick_buffer=1+BO[11,14,10,6]", "7m", {"tick_buffer": 1}, [11, 14, 10, 6], 0.007),
    # === hw_partial_pct=0 high PnL test ===
    ("hw_partial_pct=0+tick_buffer=1+BO[11,14,10,6]", "7m",
     {"tick_buffer": 1, "hw_partial_pct": 0.0}, [11, 14, 10, 6], 0.01),
    # === Conservative DD-passing reference ===
    ("risk=0.0015+BO[11,14,10,6]", "7m", {}, [11, 14, 10, 6], 0.0015),
    ("risk=0.002+BO[11,14,10,6]", "7m", {}, [11, 14, 10, 6], 0.002),
]


def main():
    print(f"=== Sweep 07b — final combos — {STRATEGY} / {SYMBOL} ===")
    print()
    rows = []
    for label, tf, overrides, hours, risk in CASES:
        params = {**BASE_V2, **overrides}
        es = _es(hours)
        s = bench(
            label=label,
            strategy_name=STRATEGY, symbol=SYMBOL, interval=tf,
            start=START, end=END, strategy_params=params,
            initial_equity=INITIAL_EQUITY, risk_per_trade=risk,
            max_contracts=MAX_CONTRACTS,
            engine_settings=es,
        )
        s["ratio_p_dd"] = round(s["net_pnl"] / s["max_dd_$"], 2) if s["max_dd_$"] > 0 else None
        s["label"], s["tf"], s["risk"], s["overrides"], s["hours"] = (
            label, tf, risk, overrides, hours
        )
        s["pass_pnl"] = s["net_pnl"] > 30_000
        s["pass_dd"] = s["max_dd_$"] < 2_500
        rows.append(s)

    print("\n=== Configs passing BOTH targets (PnL>30k AND DD<2.5k) ===")
    passing = [r for r in rows if r["pass_pnl"] and r["pass_dd"]]
    if passing:
        for r in passing:
            print(f"  ✅ {r['label']}: PnL=${r['net_pnl']:,.0f} DD=${r['max_dd_$']:,.0f}")
    else:
        print("  (none)")

    print("\n=== TOP P/DD sorted ===")
    rows_sorted = sorted(rows, key=lambda r: r["ratio_p_dd"] or -999, reverse=True)
    for r in rows_sorted:
        marker = "🎯" if r["pass_pnl"] and r["pass_dd"] else (
            "✅PnL" if r["pass_pnl"] else ("✅DD" if r["pass_dd"] else "  ")
        )
        print(f"  {marker} {r['label']:<55s} PnL=${r['net_pnl']:>9,.0f} DD=${r['max_dd_$']:>6,.0f} "
              f"N={r['trades']:>4} WR={r['win_rate']}% PF={r['profit_factor']} P/DD={r['ratio_p_dd']}")

    out = Path(__file__).resolve().parents[1] / "logs" / "07b_final_combos.json"
    out.write_text(json.dumps(rows, indent=2, default=str))
    print(f"\n[saved] {out}")


if __name__ == "__main__":
    main()
