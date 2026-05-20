"""Build the winner preset, replay-verify it, and write to data/presets.json.

WINNER config (Phase 11):
  PnL=$62,262, DD=$2,431, P/DD=25.61, N=764, WR=40.1%, PF=1.53
"""

from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE / "sweeps"))

from backend.api import BlackoutWindowSettings
from scripts.goals._shared.harness import run_backtest, summarize, fmt_summary
from scripts.goals._shared.preset import build_preset, write_preset

from _campaign import (
    BASELINE_PARAMS,
    END,
    INITIAL_EQUITY,
    INTERVAL,
    MAX_CONTRACTS,
    START,
    STRATEGY,
    SYMBOL,
    baseline_engine,
)


# Final strategy params
WINNER_STRATEGY_PARAMS = {
    "min_gap": 9,
    "rr_tp": 2.5,
    "tick_buffer": 0,
    "hw_extreme_filter_on": True,
    "rob_on": False,
    "hw_extreme": 20.0,
    "mf_smooth": 5,
    "st_atr": 14,
    "ema_sec_len": 20,
    "amp_mult": 2.5,
}

WINNER_RISK = 0.006  # 0.6%


def winner_engine():
    e = baseline_engine()
    # Add the 3 active blackouts on top of the saved-preset's 22:00-23:59 lock
    for (sh, sm, eh, em) in [(9, 0, 10, 0), (13, 0, 14, 0), (17, 0, 21, 0)]:
        e.blackout_windows.append(
            BlackoutWindowSettings(active=True, start_hour=sh, start_minute=sm,
                                   end_hour=eh, end_minute=em)
        )
    # Daily limits — after_close mode
    e.daily_win_limit_enabled = True
    e.daily_win_limit = 800.0
    e.daily_loss_limit_enabled = True
    e.daily_loss_limit = 700.0
    e.daily_limit_mode = "after_close"
    return e


def main() -> int:
    print("=" * 100)
    print("BUILD WINNER PRESET — MomentumChecker MNQ 7m")
    print("=" * 100)

    engine = winner_engine()
    full_params = dict(BASELINE_PARAMS)
    full_params.update(WINNER_STRATEGY_PARAMS)

    # Replay-verify by running the exact same backtest the preset is supposed to express
    r = run_backtest(
        strategy_name=STRATEGY,
        symbol=SYMBOL,
        interval=INTERVAL,
        start=START,
        end=END,
        strategy_params=WINNER_STRATEGY_PARAMS,  # overrides on top of default
        initial_equity=INITIAL_EQUITY,
        risk_per_trade=WINNER_RISK,
        max_contracts=MAX_CONTRACTS,
        engine_settings=engine,
    )
    s = summarize(r)
    print(f"WINNER RESULT: {fmt_summary(s)}")
    print()

    preset = build_preset(
        strategy_name=STRATEGY,
        symbol=SYMBOL,
        interval=INTERVAL,
        start=START,
        end=END,
        initial_equity=INITIAL_EQUITY,
        risk_per_trade_decimal=WINNER_RISK,
        max_contracts=MAX_CONTRACTS,
        strategy_param_overrides=WINNER_STRATEGY_PARAMS,
        engine_settings=engine,
        metrics_summary=s,
        name=f"[Auto] {STRATEGY} — {SYMBOL} {INTERVAL} — WINNER (PnL ${s['net_pnl']/1000:.1f}k / DD ${s['max_dd_$']/1000:.2f}k)",
    )

    out_path = HERE / "winner_preset.json"
    write_preset(preset, out_path, insert_into_presets_json=True)
    print(f"✅ Written to {out_path}")
    print(f"✅ Inserted into data/presets.json")
    print()
    print(f"Preset name: {preset['name']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
