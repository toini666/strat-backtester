"""07 — Fine-tune combo.

Combine best params + targeted blackouts + daily limits + risk.
Iterates on a small grid around the leading config to find the couple that
meets BOTH:
  - net PnL  > 30 000 $
  - max DD   <  2 500 $
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _campaign as C  # noqa: E402

from scripts.goals._shared.engine_settings import make_engine_settings  # noqa: E402
from scripts.goals._shared.harness import bench  # noqa: E402

TF = "7m"

# Step-03 winning combo.
BEST_PARAMS = {
    "cloud_on": True,
    "hma_pol_bars": 0,
    "signal_length": 2,
    "hyper_wave_length": 7,
    "mf_length": 25,
    "ssl_len": 80,
    "entry_window_bars": 3,
}
# Sweep 06 winners — 6 cumulative blackouts that push ratio from 5.2 → 9.2.
EXTRA_BLACKOUTS: list[dict] = [
    {"start_hour": 11, "start_minute": 0, "end_hour": 12, "end_minute": 0},
    {"start_hour": 0,  "start_minute": 0, "end_hour": 1,  "end_minute": 0},
    {"start_hour": 6,  "start_minute": 0, "end_hour": 7,  "end_minute": 0},
    {"start_hour": 8,  "start_minute": 0, "end_hour": 9,  "end_minute": 0},
    {"start_hour": 4,  "start_minute": 0, "end_hour": 5,  "end_minute": 0},
]
ACTIVATE_EXISTING: list[tuple[int, int, int, int]] = [
    (12, 0, 14, 0),  # UI-default-inactive, re-activated
]

# Risk + daily-limit grid focused around the target zone.
RISK_GRID = [0.0025, 0.003, 0.0035, 0.004]
LIMITS_GRID = [
    {"win": None, "loss": None, "mode": "intra_bar"},  # no limits
    {"win": None, "loss": 300, "mode": "intra_bar"},
    {"win": None, "loss": 400, "mode": "intra_bar"},
    {"win": None, "loss": 500, "mode": "intra_bar"},
    {"win": 300, "loss": 300, "mode": "intra_bar"},
    {"win": 400, "loss": 400, "mode": "intra_bar"},
    {"win": 500, "loss": 500, "mode": "intra_bar"},
    {"win": None, "loss": 300, "mode": "after_close"},
    {"win": None, "loss": 500, "mode": "after_close"},
    {"win": 300, "loss": 300, "mode": "after_close"},
    {"win": 500, "loss": 500, "mode": "after_close"},
]


def main():
    print(f"=== 07 FINE-TUNE COMBO — base M7 {BEST_PARAMS} ===\n")
    candidates = []
    for risk in RISK_GRID:
        for lim in LIMITS_GRID:
            es = make_engine_settings(
                C.STRATEGY,
                extra_active_windows=EXTRA_BLACKOUTS,
                activate_existing=ACTIVATE_EXISTING,
                daily_win_limit=lim["win"],
                daily_loss_limit=lim["loss"],
                daily_limit_mode=lim["mode"],
            )
            label = f"r={risk:.4f} W={lim['win']} L={lim['loss']} {lim['mode']}"
            s = bench(label,
                      strategy_name=C.STRATEGY, symbol=C.SYMBOL,
                      interval=TF, start=C.START, end=C.END,
                      strategy_params=BEST_PARAMS,
                      initial_equity=C.INITIAL_EQUITY,
                      risk_per_trade=risk,
                      max_contracts=C.MAX_CONTRACTS,
                      engine_settings=es)
            s["__risk"] = risk
            s["__lim"] = lim
            candidates.append(s)

    print("\n--- Candidates meeting BOTH goals ---")
    passing = [s for s in candidates
               if s["net_pnl"] > C.TARGET_PNL and s["max_dd_$"] < C.TARGET_MAX_DD]
    if not passing:
        print("  ❌ none meet both goals yet — best by ratio:")
        passing = sorted(candidates,
                         key=lambda x: x["net_pnl"] / max(x["max_dd_$"], 1.0),
                         reverse=True)[:5]
    else:
        passing.sort(key=lambda x: x["net_pnl"] / max(x["max_dd_$"], 1.0), reverse=True)
    for s in passing[:10]:
        print(f"  {s['label']:<60s} {s['net_pnl']:>10,.0f}  DD={s['max_dd_$']:>6,.0f}  "
              f"PF={s['profit_factor']}  N={s['trades']}  "
              f"ratio={s['net_pnl']/max(s['max_dd_$'],1):.2f}")


if __name__ == "__main__":
    main()
