"""08 — Final validation.

Winner found in sweep 07c:
  signal_length=4, sig_extreme=30 + combo + 5 blackouts, r=0.0034
  → PnL $30,313 / DD $1,960 / PF 1.51 / WR 47.5% / N=998

Re-run + 5 nearby alternatives, in foreground for the final REPORT.
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
    "signal_length": 4,
    "sig_extreme": 30,
    "hyper_wave_length": 7,
    "mf_length": 25,
    "ssl_len": 80,
    "entry_window_bars": 3,
}
EXTRA_BLACKOUTS = [
    {"start_hour": 11, "start_minute": 0, "end_hour": 12, "end_minute": 0},
    {"start_hour": 0,  "start_minute": 0, "end_hour": 1,  "end_minute": 0},
    {"start_hour": 6,  "start_minute": 0, "end_hour": 7,  "end_minute": 0},
    {"start_hour": 8,  "start_minute": 0, "end_hour": 9,  "end_minute": 0},
    {"start_hour": 4,  "start_minute": 0, "end_hour": 5,  "end_minute": 0},
]
ACTIVATE_EXISTING = [(12, 0, 14, 0)]

WINNER_RISK = 0.0034


def es():
    return make_engine_settings(C.STRATEGY,
                                activate_existing=ACTIVATE_EXISTING,
                                extra_active_windows=EXTRA_BLACKOUTS)


def main():
    print(f"=== 08 FINAL VALIDATION — full period ===\n", flush=True)
    print(f"Target: PnL > ${C.TARGET_PNL:,.0f}  &  DD < ${C.TARGET_MAX_DD:,.0f}\n",
          flush=True)

    s = bench("WINNER (sl=4 se=30 r=0.0034)",
              strategy_name=C.STRATEGY, symbol=C.SYMBOL, interval=TF,
              start=C.START, end=C.END, strategy_params=BASE_PARAMS,
              initial_equity=C.INITIAL_EQUITY, risk_per_trade=WINNER_RISK,
              max_contracts=C.MAX_CONTRACTS, engine_settings=es())
    pnl_ok = s["net_pnl"] > C.TARGET_PNL
    dd_ok = s["max_dd_$"] < C.TARGET_MAX_DD
    print(f"\n  PnL goal: {'✅' if pnl_ok else '❌'}  "
          f"({s['net_pnl']:,.0f} vs {C.TARGET_PNL:,.0f})")
    print(f"  DD  goal: {'✅' if dd_ok else '❌'}  "
          f"({s['max_dd_$']:,.0f} vs {C.TARGET_MAX_DD:,.0f})\n", flush=True)

    print("--- Alternatives ---", flush=True)
    alts = [
        ("ALT1 r=0.0035",  dict(BASE_PARAMS), 0.0035),
        ("ALT2 r=0.0033",  dict(BASE_PARAMS), 0.0033),
        ("ALT3 sl=3 se=35 r=0.0031", {**BASE_PARAMS, "signal_length": 3, "sig_extreme": 35}, 0.0031),
        ("ALT4 sl=4 se=20 r=0.0033", {**BASE_PARAMS, "sig_extreme": 20}, 0.0033),
        ("ALT5 sl=4 se=30 r=0.0029", dict(BASE_PARAMS), 0.0029),
    ]
    for label, p, r in alts:
        bench(label, strategy_name=C.STRATEGY, symbol=C.SYMBOL, interval=TF,
              start=C.START, end=C.END, strategy_params=p,
              initial_equity=C.INITIAL_EQUITY, risk_per_trade=r,
              max_contracts=C.MAX_CONTRACTS, engine_settings=es())


if __name__ == "__main__":
    main()
