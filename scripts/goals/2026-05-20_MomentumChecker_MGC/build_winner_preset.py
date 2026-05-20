"""Build the winner preset, replay-verify it, and write to data/presets.json.

WINNER config (Phase 10):
  PnL=$56,353, DD=$2,425, P/DD=23.24, N=784, WR=41.3%, PF=1.49
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


# Final strategy params (overrides on top of MomentumChecker.default_params)
WINNER_STRATEGY_PARAMS = {
    "min_gap":               8,
    "sl_lookback":           15,
    "rr_tp":                 3.0,
    "sl_max_points":         50.0,
    "ut_on":                 False,
    "sig_extreme_filter_on": True,
    "hw_extreme":            15.0,
    "stc_length":            10,
    "stc_fast_len":          32,
}

WINNER_RISK = 0.006  # 0.6%


def winner_engine():
    """Engine settings for the winner.

    Base 22:00-23:59 blackout (from baseline_engine) + add the two campaign-found
    losing-hour blackouts as ACTIVE: 12:30-14:00 (lunch) and 17:00-21:00 (US PM).
    """
    e = baseline_engine()
    for (sh, sm, eh, em) in [(12, 30, 14, 0), (17, 0, 21, 0)]:
        e.blackout_windows.append(
            BlackoutWindowSettings(active=True, start_hour=sh, start_minute=sm,
                                   end_hour=eh, end_minute=em)
        )
    # No daily win/loss limits — per user instruction.
    return e


def main() -> int:
    print("=" * 100)
    print("BUILD WINNER PRESET — MomentumChecker MGC 7m")
    print("=" * 100)

    engine = winner_engine()

    r = run_backtest(
        strategy_name=STRATEGY,
        symbol=SYMBOL,
        interval=INTERVAL,
        start=START,
        end=END,
        strategy_params=WINNER_STRATEGY_PARAMS,
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
        name=f"[Auto] {STRATEGY} — {SYMBOL} {INTERVAL} — WINNER "
             f"(PnL ${s['net_pnl']/1000:.1f}k / DD ${s['max_dd_$']/1000:.2f}k)",
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
