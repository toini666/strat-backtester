"""Sweep 07 — Fine-tune the risk + alt-params combo with BO[11,14,10,6] blackouts.

BASE_V3 = BASE_V2 + BO[11,14,10,6] blackouts
At risk=0.01 the base is PnL=$45,281, DD=$6,717, P/DD=6.74.

Step A — fine risk grid (find best PnL with DD<2.5k)
Step B — alternative param singles on top of BASE_V3 (look for further DD reduction)
Step C — combine the most promising alt-param with risk fine-tune
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
BLACKOUT_HOURS = [11, 14, 10, 6]


def _es():
    return make_engine_settings(
        STRATEGY,
        extra_active_windows=[
            {"start_hour": h, "start_minute": 0, "end_hour": h + 1, "end_minute": 0}
            for h in BLACKOUT_HOURS
        ],
    )


# Step A — fine risk grid
RISKS = [0.0008, 0.001, 0.0015, 0.002, 0.0025, 0.003, 0.0035, 0.004, 0.005, 0.006,
         0.008, 0.009, 0.01, 0.011, 0.012, 0.013, 0.014]

# Step B — alt-param singles on top of BASE_V2+BO
ALT_SINGLES = [
    {"hma1_len": 21},
    {"hma2_len": 25},
    {"hma_pol_bars": 1},
    {"hma_pol_bars": 0},
    {"hyper_wave_length": 5, "signal_length": 2},
    {"signal_candle_sl_on": False},
    {"signal_candle_sl_on": False, "hma_pol_bars": 1},
    {"exit_mode": "inversion_hma"},
    {"exit_mode": "both_hma"},
    {"hw_partial_pct": 0.0},          # disable HW partial — 03 showed +PnL but worse DD
    {"hw_partial_pct": 50.0},
    {"hw_partial_pct": 25.0, "hw_partial_min_rr": 0.5},
    {"max_candle_pct": 0.5},
    {"max_candle_pct": 0.0},
    {"sl_mode": "ssl_extreme"},
    {"sl_mode": "cross_hma"},
    {"tick_buffer": 1},
    {"block_loss_exit_before_partial": False},
    {"cloud_on": True},
]


def main():
    print(f"=== Sweep 07 — fine-tune — {STRATEGY} / {SYMBOL} / {TF} ===")
    print(f"    BASE_V2 = {BASE_V2}")
    print(f"    Blackouts = H={BLACKOUT_HOURS}")
    print()

    rows = []
    es = _es()

    print("--- A. fine risk grid ---")
    for r in RISKS:
        s = bench(
            label=f"risk={r}",
            strategy_name=STRATEGY, symbol=SYMBOL, interval=TF,
            start=START, end=END, strategy_params=BASE_V2,
            initial_equity=INITIAL_EQUITY, risk_per_trade=r,
            max_contracts=MAX_CONTRACTS,
            engine_settings=es,
        )
        s["ratio_p_dd"] = round(s["net_pnl"] / s["max_dd_$"], 2) if s["max_dd_$"] > 0 else None
        s["label"], s["risk"] = f"risk={r}", r
        rows.append(s)

    # find candidates that pass DD < 2500
    print("\n  Configs passing DD<$2500:")
    for r in rows:
        if r["max_dd_$"] < 2500:
            print(f"    risk={r['risk']} → PnL=${r['net_pnl']:,.0f} DD=${r['max_dd_$']:,.0f} "
                  f"P/DD={r['ratio_p_dd']}")

    print("\n--- B. alt-param singles at risk=0.01 ---")
    for alt in ALT_SINGLES:
        params = {**BASE_V2, **alt}
        label = "+".join(f"{k}={v}" for k, v in alt.items())
        s = bench(
            label=label,
            strategy_name=STRATEGY, symbol=SYMBOL, interval=TF,
            start=START, end=END, strategy_params=params,
            initial_equity=INITIAL_EQUITY, risk_per_trade=0.01,
            max_contracts=MAX_CONTRACTS,
            engine_settings=es,
        )
        s["ratio_p_dd"] = round(s["net_pnl"] / s["max_dd_$"], 2) if s["max_dd_$"] > 0 else None
        s["label"] = label
        rows.append(s)

    print("\n=== TOP 20 — sorted by P/DD ===")
    rows_sorted = sorted(rows, key=lambda r: r["ratio_p_dd"] or -999, reverse=True)
    for r in rows_sorted[:25]:
        print(f"  {r['label']:<60s} PnL=${r['net_pnl']:>9,.0f} DD=${r['max_dd_$']:>6,.0f} "
              f"N={r['trades']:>4} WR={r['win_rate']}% PF={r['profit_factor']} P/DD={r['ratio_p_dd']}")

    out = Path(__file__).resolve().parents[1] / "logs" / "07_finetune.json"
    out.write_text(json.dumps(rows, indent=2, default=str))
    print(f"\n[saved] {out}")


if __name__ == "__main__":
    main()
