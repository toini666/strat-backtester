"""04 — Risk per trade & daily limits.

Base = M7 + best params from sweep 03 combined.

Daily limits:
- intra_bar FIRST (CME-side stops as soon as floating PnL hits the cap)
- after_close fallback
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _campaign as C  # noqa: E402

from scripts.goals._shared.engine_settings import make_engine_settings  # noqa: E402
from scripts.goals._shared.harness import bench  # noqa: E402

TF = "7m"
# Top-of-step-03 params (updated after step 03 final ratios are known).
BASE_PARAMS = {
    "cloud_on": True,
    "hma_pol_bars": 0,
    "signal_length": 2,
    "hyper_wave_length": 7,
    "mf_length": 25,
    "ssl_len": 80,
    "entry_window_bars": 3,
}


def main():
    print(f"=== 04 RISK & DAILY LIMITS — base M7 {BASE_PARAMS} ===\n", flush=True)

    # Combined base
    bench("COMBO base (no limits)", strategy_name=C.STRATEGY, symbol=C.SYMBOL,
          interval=TF, start=C.START, end=C.END,
          strategy_params=BASE_PARAMS, initial_equity=C.INITIAL_EQUITY,
          risk_per_trade=C.DEFAULT_RISK, max_contracts=C.MAX_CONTRACTS)

    # Risk sweep
    print("\n--- Risk per trade sweep (no limits) ---", flush=True)
    for risk in (0.002, 0.003, 0.004, 0.005, 0.0075, 0.01, 0.015):
        bench(f"r={risk:.4f}", strategy_name=C.STRATEGY, symbol=C.SYMBOL,
              interval=TF, start=C.START, end=C.END,
              strategy_params=BASE_PARAMS, initial_equity=C.INITIAL_EQUITY,
              risk_per_trade=risk, max_contracts=C.MAX_CONTRACTS)

    for mode in ("intra_bar", "after_close"):
        print(f"\n--- Daily limits {mode!r} (r=0.005) ---", flush=True)
        for wl, ll in [(None, 300), (None, 500), (None, 750), (None, 1000),
                       (300, 300), (500, 500), (750, 750), (1000, 1000),
                       (500, 1000), (1000, 500)]:
            es = make_engine_settings(C.STRATEGY,
                                      daily_win_limit=wl, daily_loss_limit=ll,
                                      daily_limit_mode=mode)
            bench(f"{mode} W={wl} L={ll}",
                  strategy_name=C.STRATEGY, symbol=C.SYMBOL,
                  interval=TF, start=C.START, end=C.END,
                  strategy_params=BASE_PARAMS,
                  initial_equity=C.INITIAL_EQUITY,
                  risk_per_trade=0.005,
                  max_contracts=C.MAX_CONTRACTS,
                  engine_settings=es)


if __name__ == "__main__":
    main()
