"""07b — Alternative combos & TFs (executed only if 07 doesn't hit goal).

Explore:
  - Other timeframes (M5, M3) with combo+blackouts
  - Less aggressive signal_length variants
  - Tighter sig_extreme
  - signal_candle_sl_on=True / cooldown variations
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _campaign as C  # noqa: E402

from scripts.goals._shared.engine_settings import make_engine_settings  # noqa: E402
from scripts.goals._shared.harness import bench  # noqa: E402


BASE_PARAMS = {
    "cloud_on": True,
    "hma_pol_bars": 0,
    "signal_length": 2,
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


def es(daily_win=None, daily_loss=None, mode="intra_bar"):
    return make_engine_settings(
        C.STRATEGY,
        activate_existing=ACTIVATE_EXISTING,
        extra_active_windows=EXTRA_BLACKOUTS,
        daily_win_limit=daily_win,
        daily_loss_limit=daily_loss,
        daily_limit_mode=mode,
    )


def main():
    print(f"=== 07b ALT COMBOS — combo + 5 extra blackouts ===\n", flush=True)

    # Test other TFs with combo + blackouts
    print("\n--- Other TFs with same params + blackouts (no daily limits, r=0.005) ---", flush=True)
    for tf in ("3m", "5m", "10m"):
        bench(f"TF={tf}", strategy_name=C.STRATEGY, symbol=C.SYMBOL, interval=tf,
              start=C.START, end=C.END, strategy_params=BASE_PARAMS,
              initial_equity=C.INITIAL_EQUITY, risk_per_trade=0.005,
              max_contracts=C.MAX_CONTRACTS, engine_settings=es())

    # Less aggressive signal_length variants at M7
    print("\n--- M7: signal_length variants (r=0.005, no limits) ---", flush=True)
    for sl in (2, 3, 5):
        p = dict(BASE_PARAMS); p["signal_length"] = sl
        bench(f"signal_length={sl}", strategy_name=C.STRATEGY, symbol=C.SYMBOL,
              interval="7m", start=C.START, end=C.END, strategy_params=p,
              initial_equity=C.INITIAL_EQUITY, risk_per_trade=0.005,
              max_contracts=C.MAX_CONTRACTS, engine_settings=es())

    # Tighter sig_extreme variants on M7
    print("\n--- M7: sig_extreme variants (r=0.005, no limits) ---", flush=True)
    for se in (15, 20, 25, 35):
        p = dict(BASE_PARAMS); p["sig_extreme"] = se
        bench(f"sig_extreme={se}", strategy_name=C.STRATEGY, symbol=C.SYMBOL,
              interval="7m", start=C.START, end=C.END, strategy_params=p,
              initial_equity=C.INITIAL_EQUITY, risk_per_trade=0.005,
              max_contracts=C.MAX_CONTRACTS, engine_settings=es())

    # Tighter combos
    print("\n--- M7: targeted combos ---", flush=True)
    targeted = [
        ("sig_extreme=20+sl=2", {"sig_extreme": 20, "signal_length": 2}),
        ("sig_extreme=25+sl=3", {"sig_extreme": 25, "signal_length": 3}),
        ("sig_extreme=25+entry_w=5", {"sig_extreme": 25, "entry_window_bars": 5}),
        ("ssl_mult=0.3", {"ssl_mult": 0.3}),
        ("hyper_wave_length=9+signal_length=3", {"hyper_wave_length": 9, "signal_length": 3}),
    ]
    for label, ov in targeted:
        p = dict(BASE_PARAMS); p.update(ov)
        bench(label, strategy_name=C.STRATEGY, symbol=C.SYMBOL,
              interval="7m", start=C.START, end=C.END, strategy_params=p,
              initial_equity=C.INITIAL_EQUITY, risk_per_trade=0.005,
              max_contracts=C.MAX_CONTRACTS, engine_settings=es())


if __name__ == "__main__":
    main()
