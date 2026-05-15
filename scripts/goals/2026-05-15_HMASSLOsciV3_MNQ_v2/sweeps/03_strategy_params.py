"""03 — Strategy core params (focused 1-D sweeps).

Base = M7 + cloud_on=True + hma_pol_bars=0 (winner of step 02).
Tight 1-D sweep on highest-impact knobs only.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _campaign as C  # noqa: E402

from scripts.goals._shared.harness import bench  # noqa: E402

TF = "7m"
BASE = {"cloud_on": True, "hma_pol_bars": 0}


def sweep(key, values):
    print(f"\n--- {key} ---", flush=True)
    res = []
    for v in values:
        overrides = dict(BASE)
        overrides[key] = v
        s = bench(f"{key}={v}", strategy_name=C.STRATEGY, symbol=C.SYMBOL,
                  interval=TF, start=C.START, end=C.END,
                  strategy_params=overrides, initial_equity=C.INITIAL_EQUITY,
                  risk_per_trade=C.DEFAULT_RISK, max_contracts=C.MAX_CONTRACTS)
        s["__label"] = f"{key}={v}"
        res.append(s)
    best = max(res, key=lambda s: s["net_pnl"] / max(s["max_dd_$"], 1.0))
    print(f"  best by ratio: {best['__label']} "
          f"PnL=${best['net_pnl']:>9,.0f} DD=${best['max_dd_$']:>6,.0f} "
          f"ratio={best['net_pnl']/max(best['max_dd_$'],1):.2f}", flush=True)
    return best


def main():
    print(f"=== 03 CORE PARAMS — base M7 {BASE} ===\n", flush=True)
    bench("BASE", strategy_name=C.STRATEGY, symbol=C.SYMBOL,
          interval=TF, start=C.START, end=C.END,
          strategy_params=BASE, initial_equity=C.INITIAL_EQUITY,
          risk_per_trade=C.DEFAULT_RISK, max_contracts=C.MAX_CONTRACTS)
    sweep("sig_extreme", [15, 20, 25, 30, 35])
    sweep("signal_length", [2, 3, 4, 5])
    sweep("hyper_wave_length", [3, 5, 7, 9])
    sweep("mf_length", [25, 35, 45])
    sweep("ssl_len", [40, 60, 80, 100])
    sweep("entry_window_bars", [3, 5, 8, 12])
    sweep("max_sl_points", [100, 200, 300, 500])
    sweep("hma1_len", [9, 13, 21])
    sweep("hma2_len", [17, 21, 34])
    sweep("max_candle_pct", [0.0, 0.5, 0.9])
    sweep("cooldown_bars", [0, 1, 2, 3])


if __name__ == "__main__":
    main()
