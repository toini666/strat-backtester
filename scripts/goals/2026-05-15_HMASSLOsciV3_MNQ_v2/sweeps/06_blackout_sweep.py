"""06 — Blackout sweeps targeting the losing hours from sweep 05.

Hour analysis findings (M7 + combo, no limits, r=0.01):
  H=11  total=-$10,352  (n=83)   ← biggest drag
  H=12  total= -$6,239  (n=70)
  H=00  total= -$5,073  (n=59)
  H=06  total= -$3,185  (n=38)
  H=08  total= -$2,556  (n=58)
  H=04  total= -$2,283  (n=39)

UI defaults: only 22:00–23:59 is active for HMASSLOsciV3. The window
12:00–14:00 is defined but inactive — we re-activate it.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _campaign as C  # noqa: E402

from scripts.goals._shared.engine_settings import make_engine_settings  # noqa: E402
from scripts.goals._shared.harness import bench  # noqa: E402

TF = "7m"
BASE_PARAMS = {
    "cloud_on": True,
    "hma_pol_bars": 0,
    "signal_length": 2,
    "hyper_wave_length": 7,
    "mf_length": 25,
    "ssl_len": 80,
    "entry_window_bars": 3,
}
RISK = 0.01  # raw scaling — daily limits will be re-applied later
DAILY_WIN = None
DAILY_LOSS = None
DAILY_MODE = "intra_bar"


def make_es(activate=(), extra=()):
    return make_engine_settings(
        C.STRATEGY,
        activate_existing=list(activate),
        extra_active_windows=list(extra),
        daily_win_limit=DAILY_WIN,
        daily_loss_limit=DAILY_LOSS,
        daily_limit_mode=DAILY_MODE,
    )


def main():
    print(f"=== 06 BLACKOUT SWEEPS — base M7 {BASE_PARAMS}  risk={RISK} ===\n",
          flush=True)
    bench("baseline (UI defaults: only 22-23:59)",
          strategy_name=C.STRATEGY, symbol=C.SYMBOL, interval=TF,
          start=C.START, end=C.END, strategy_params=BASE_PARAMS,
          initial_equity=C.INITIAL_EQUITY, risk_per_trade=RISK,
          max_contracts=C.MAX_CONTRACTS, engine_settings=make_es())

    print("\n--- Individual losing-hour blackouts ---", flush=True)
    individual = [
        ("+11-12", [{"start_hour": 11, "start_minute": 0,
                     "end_hour": 12, "end_minute": 0}]),
        ("activate 12-14 default", []),  # via activate_existing below
        ("+00-01", [{"start_hour": 0, "start_minute": 0,
                     "end_hour": 1, "end_minute": 0}]),
        ("+06-07", [{"start_hour": 6, "start_minute": 0,
                     "end_hour": 7, "end_minute": 0}]),
        ("+08-09", [{"start_hour": 8, "start_minute": 0,
                     "end_hour": 9, "end_minute": 0}]),
        ("+04-05", [{"start_hour": 4, "start_minute": 0,
                     "end_hour": 5, "end_minute": 0}]),
    ]
    for label, extra in individual:
        activate = []
        if label == "activate 12-14 default":
            activate = [(12, 0, 14, 0)]
        bench(label, strategy_name=C.STRATEGY, symbol=C.SYMBOL, interval=TF,
              start=C.START, end=C.END, strategy_params=BASE_PARAMS,
              initial_equity=C.INITIAL_EQUITY, risk_per_trade=RISK,
              max_contracts=C.MAX_CONTRACTS,
              engine_settings=make_es(activate=activate, extra=extra))

    print("\n--- Cumulative additive blackouts ---", flush=True)
    cum_extras: list[dict] = []
    cum_activate: list[tuple[int, int, int, int]] = []
    additions = [
        ("+11-12",    [{"start_hour": 11, "start_minute": 0,
                        "end_hour": 12, "end_minute": 0}], None),
        ("+11-12 +12-14",  [], (12, 0, 14, 0)),
        ("+11-12 +12-14 +00-01",
         [{"start_hour": 0, "start_minute": 0,
           "end_hour": 1, "end_minute": 0}], None),
        ("+11-12 +12-14 +00-01 +06-07",
         [{"start_hour": 6, "start_minute": 0,
           "end_hour": 7, "end_minute": 0}], None),
        ("+11-12 +12-14 +00-01 +06-07 +08-09",
         [{"start_hour": 8, "start_minute": 0,
           "end_hour": 9, "end_minute": 0}], None),
        ("+11-12 +12-14 +00-01 +06-07 +08-09 +04-05",
         [{"start_hour": 4, "start_minute": 0,
           "end_hour": 5, "end_minute": 0}], None),
    ]
    for label, add_extra, add_act in additions:
        cum_extras = cum_extras + add_extra
        if add_act is not None:
            cum_activate = cum_activate + [add_act]
        bench(label, strategy_name=C.STRATEGY, symbol=C.SYMBOL, interval=TF,
              start=C.START, end=C.END, strategy_params=BASE_PARAMS,
              initial_equity=C.INITIAL_EQUITY, risk_per_trade=RISK,
              max_contracts=C.MAX_CONTRACTS,
              engine_settings=make_es(activate=cum_activate, extra=cum_extras))


if __name__ == "__main__":
    main()
