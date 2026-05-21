"""Build ALTERNATIVE presets (revised):

  ALT-PNL-PRIORITY: P6 anchor + sl_max=41 + r=0.65% (PnL≥seed strict, DD slightly over $2,500)
    → PnL=$80,790 / $DD=$2,539

  ALT-HIGHPNL: P6 anchor + sl_max=41 + BO=01-02 + r=0.66% (max PnL gain)
    → PnL=$88,247 / $DD=$2,845
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

CAMPAIGN_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(CAMPAIGN_DIR / "sweeps"))

from backend.api import BacktestEngineSettings, BlackoutWindowSettings  # noqa: E402
from scripts.goals._shared.harness import run_backtest, summarize, fmt_summary  # noqa: E402
from scripts.goals._shared.preset import build_preset, write_preset  # noqa: E402

from _campaign import (  # noqa: E402
    BASELINE_PARAMS, END, INITIAL_EQUITY, INTERVAL, MAX_CONTRACTS,
    START, STRATEGY, SYMBOL,
)


P6_BASE = dict(BASELINE_PARAMS)
P6_BASE.update({
    "sl_max_points": 40.0,
    "tick_buffer": 2,
    "pts_ema_align": 2,
    "min_gap": 10,
})


def seed_only_engine() -> BacktestEngineSettings:
    return BacktestEngineSettings(
        auto_close_enabled=True, auto_close_hour=22, auto_close_minute=0,
        blackout_windows=[
            BlackoutWindowSettings(active=True, start_hour=9,  start_minute=0,  end_hour=10, end_minute=0),
            BlackoutWindowSettings(active=True, start_hour=13, start_minute=0,  end_hour=14, end_minute=30),
            BlackoutWindowSettings(active=True, start_hour=17, start_minute=0,  end_hour=23, end_minute=59),
            BlackoutWindowSettings(active=True, start_hour=22, start_minute=0,  end_hour=23, end_minute=59),
        ],
        debug=False,
        daily_win_limit_enabled=False, daily_win_limit=800.0,
        daily_loss_limit_enabled=False, daily_loss_limit=700.0,
        daily_limit_mode="after_close",
    )


def engine_with_01_02() -> BacktestEngineSettings:
    return BacktestEngineSettings(
        auto_close_enabled=True, auto_close_hour=22, auto_close_minute=0,
        blackout_windows=[
            BlackoutWindowSettings(active=True, start_hour=1,  start_minute=0,  end_hour=2,  end_minute=0),
            BlackoutWindowSettings(active=True, start_hour=9,  start_minute=0,  end_hour=10, end_minute=0),
            BlackoutWindowSettings(active=True, start_hour=13, start_minute=0,  end_hour=14, end_minute=30),
            BlackoutWindowSettings(active=True, start_hour=17, start_minute=0,  end_hour=23, end_minute=59),
            BlackoutWindowSettings(active=True, start_hour=22, start_minute=0,  end_hour=23, end_minute=59),
        ],
        debug=False,
        daily_win_limit_enabled=False, daily_win_limit=800.0,
        daily_loss_limit_enabled=False, daily_loss_limit=700.0,
        daily_limit_mode="after_close",
    )


def run_and_write(params, risk, engine, suffix, path_suffix):
    result = run_backtest(
        strategy_name=STRATEGY, symbol=SYMBOL, interval=INTERVAL,
        start=START, end=END,
        initial_equity=INITIAL_EQUITY,
        risk_per_trade=risk,
        max_contracts=MAX_CONTRACTS,
        engine_settings=engine,
        strategy_params=params,
    )
    s = summarize(result)
    print(f"\n[{suffix}] risk={risk*100:.2f}% → {fmt_summary(s)}")

    preset = build_preset(
        strategy_name=STRATEGY, symbol=SYMBOL, interval=INTERVAL,
        start=START, end=END, initial_equity=INITIAL_EQUITY,
        risk_per_trade_decimal=risk, max_contracts=MAX_CONTRACTS,
        strategy_param_overrides=params, engine_settings=engine,
        metrics_summary=s,
        name=f"[Auto] MomentumCheckerV2 — MNQ 7m — v3 {suffix} (PnL ${s['net_pnl']/1000:.1f}k / DD ${s['max_dd_$']/1000:.2f}k / P/DD {s['net_pnl']/max(s['max_dd_$'],1):.1f})",
    )
    preset_path = CAMPAIGN_DIR / path_suffix
    write_preset(preset, preset_path, insert_into_presets_json=True)
    print(f"Wrote {preset_path}")


def main() -> int:
    print("=" * 100)
    print("BUILDING ALTERNATIVE PRESETS (revised) — MomentumCheckerV2 MNQ 7m v3")
    print("=" * 100)

    # ALT-PNL-PRIORITY: PnL≥seed strict, DD close to $2,500
    p1 = dict(P6_BASE); p1.update({"sl_max_points": 41.0})
    run_and_write(p1, 0.0065, seed_only_engine(), "ALT-PNLSTRICT",
                  "alt_pnl_strict_preset.json")

    # ALT-HIGHPNL: P6 + sl_max=41 + BO=01-02 + r=0.66% → highest PnL gain
    run_and_write(p1, 0.0066, engine_with_01_02(), "ALT-HIGHPNL",
                  "alt_high_pnl_preset.json")

    return 0


if __name__ == "__main__":
    sys.exit(main())
