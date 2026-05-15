"""07c — Tight finetune around the high-ratio zone.

Sweep 07b found signal_length=3 (default!) + sig_extreme=15-25 has highest
ratio (~10-11.5). The actual aggressive default signal_length=2 was
sub-optimal.  Test the (sig_extreme × signal_length × risk) grid in the
close zone and see if we can crack the goal.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _campaign as C  # noqa: E402

from scripts.goals._shared.engine_settings import make_engine_settings  # noqa: E402
from scripts.goals._shared.harness import bench  # noqa: E402

TF = "7m"
BASE_NO_SL = {  # base params WITHOUT signal_length / sig_extreme — those are swept
    "cloud_on": True,
    "hma_pol_bars": 0,
    "hyper_wave_length": 7,
    "mf_length": 25,
    "ssl_len": 80,
    "entry_window_bars": 3,
}
EXTRA = [
    {"start_hour": 11, "start_minute": 0, "end_hour": 12, "end_minute": 0},
    {"start_hour": 0,  "start_minute": 0, "end_hour": 1,  "end_minute": 0},
    {"start_hour": 6,  "start_minute": 0, "end_hour": 7,  "end_minute": 0},
    {"start_hour": 8,  "start_minute": 0, "end_hour": 9,  "end_minute": 0},
    {"start_hour": 4,  "start_minute": 0, "end_hour": 5,  "end_minute": 0},
]
ACTIVATE = [(12, 0, 14, 0)]


def es(daily_win=None, daily_loss=None, mode="intra_bar"):
    return make_engine_settings(
        C.STRATEGY,
        activate_existing=ACTIVATE,
        extra_active_windows=EXTRA,
        daily_win_limit=daily_win,
        daily_loss_limit=daily_loss,
        daily_limit_mode=mode,
    )


def main():
    print(f"=== 07c TIGHT FINETUNE — signal_length × sig_extreme × risk ===\n",
          flush=True)

    # 2D sweep on signal_length × sig_extreme (no daily limits, r=0.005)
    print("--- signal_length × sig_extreme (r=0.005, no limits) ---", flush=True)
    candidates = []
    for sl in (2, 3, 4):
        for se in (15, 20, 25, 30, 35):
            p = dict(BASE_NO_SL)
            p["signal_length"] = sl
            p["sig_extreme"] = se
            s = bench(f"sl={sl} se={se}", strategy_name=C.STRATEGY,
                      symbol=C.SYMBOL, interval=TF, start=C.START, end=C.END,
                      strategy_params=p,
                      initial_equity=C.INITIAL_EQUITY,
                      risk_per_trade=0.005,
                      max_contracts=C.MAX_CONTRACTS, engine_settings=es())
            s["__cfg"] = (sl, se)
            candidates.append(s)

    print("\n--- Top 5 by Profit/DD ratio @ r=0.005 ---", flush=True)
    candidates.sort(key=lambda x: x["net_pnl"] / max(x["max_dd_$"], 1),
                    reverse=True)
    for s in candidates[:5]:
        ratio = s["net_pnl"] / max(s["max_dd_$"], 1)
        print(f"  sl={s['__cfg'][0]} se={s['__cfg'][1]}  "
              f"PnL=${s['net_pnl']:>9,.0f}  DD=${s['max_dd_$']:>6,.0f}  "
              f"PF={s['profit_factor']}  N={s['trades']}  ratio={ratio:.2f}",
              flush=True)

    # For the top 3 ratios, scale risk to hit exactly DD≈$2.5k
    print("\n--- Risk scaling on top candidates ---", flush=True)
    for s in candidates[:3]:
        sl, se = s["__cfg"]
        # Compute risk_per_trade to hit target DD
        target_risk = 0.005 * (C.TARGET_MAX_DD * 0.95 / max(s["max_dd_$"], 1))
        target_risk = max(0.001, min(target_risk, 0.01))
        p = dict(BASE_NO_SL)
        p["signal_length"] = sl
        p["sig_extreme"] = se
        for r in [target_risk - 0.0005, target_risk, target_risk + 0.0005]:
            bench(f"sl={sl} se={se} r={r:.4f}",
                  strategy_name=C.STRATEGY, symbol=C.SYMBOL, interval=TF,
                  start=C.START, end=C.END, strategy_params=p,
                  initial_equity=C.INITIAL_EQUITY, risk_per_trade=r,
                  max_contracts=C.MAX_CONTRACTS, engine_settings=es())


if __name__ == "__main__":
    main()
