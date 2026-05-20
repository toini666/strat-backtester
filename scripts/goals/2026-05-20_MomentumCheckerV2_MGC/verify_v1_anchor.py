"""Verify V1 MGC anchor's TRUE $DD under the patched simulator.

The V1 MGC preset ("New base MomentumChecker — MGC 7m — WINNER (PnL $56.4k
/ DD $2.43k)") stores `max_drawdown: 4.74%`, which suggests its DD was
reported using the % × initial path (the buggy approach). This script runs
that preset's exact params through the patched simulator on `MomentumChecker`
(V1 strategy) to record the TRUE $-DD.

This baseline matters for the campaign because the user's hard ceiling is
$2,500. If V1 MGC's true DD is already above that, the campaign must
target *tighter than V1*, not Pareto-improve from it.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from scripts.goals._shared.harness import bench  # noqa: E402
from backend.api import BacktestEngineSettings, BlackoutWindowSettings  # noqa: E402


# Exact V1 MGC preset params (from data/presets.json)
V1_MGC_PARAMS = {
    "long_prep_threshold": 3, "long_threshold": 5,
    "short_prep_threshold": 3, "short_threshold": 5,
    "min_gap": 8, "max_candle_pct": 0.4,
    "sl_lookback": 15, "sl_max_points": 50.0, "rr_tp": 3.0, "tick_buffer": 2,
    "osc_on": True, "hyper_wave_length": 5, "signal_type": "SMA", "signal_length": 3,
    "mf_length": 35, "mf_smooth": 6,
    "hw_filter_on": True, "hw_level": 16.0,
    "hw_extreme_filter_on": False, "sig_extreme_filter_on": True, "hw_extreme": 15.0,
    "pts_hw_sens": 1, "pts_hw_value": 1, "pts_hw_extreme": 1, "pts_sig_extreme": 1,
    "pts_cloud": 1, "pts_delta": 1,
    "ema_on": True, "ema_prin_len": 30, "ema_sec_len": 9,
    "pts_ema_break": 1, "pts_ema_align": 1,
    "st_on": True, "st_atr": 10, "st_mult": 3.0, "pts_st": 1,
    "alligator_on": True, "jaw_length": 13, "teeth_length": 8, "lips_length": 5,
    "jaw_offset": 8, "teeth_offset": 5, "lips_offset": 3,
    "pts_alligator": 1, "pts_alli_offset": 1, "pts_retest_lips": 1,
    "ut_on": False, "ut_key": 1.0, "ut_atr_period": 10,
    "use_heikin_ashi": False, "pts_ut_bot": 1,
    "rob_on": True, "pts_rob": 1,
    "stc_on": True, "stc_length": 10, "stc_fast_len": 32, "stc_slow_len": 50,
    "stc_min_long": 1.0, "stc_max_long": 99.0, "stc_min_short": 1.0, "stc_max_short": 99.0,
    "pts_stc": 1,
    "hma_on": True, "hma_ema_len": 7, "hma1_len": 42, "hma2_len": 84,
    "amp_mult": 2.0, "pts_hma_break": 1,
    "tick_size": 0.25,
}


def v1_mgc_engine():
    """V1 MGC's exact engine settings (from preset)."""
    return BacktestEngineSettings(
        auto_close_enabled=True,
        auto_close_hour=22,
        auto_close_minute=0,
        blackout_windows=[
            # active=true windows from preset
            BlackoutWindowSettings(active=True,  start_hour=22, start_minute=0,
                                   end_hour=23, end_minute=59),
            BlackoutWindowSettings(active=True,  start_hour=12, start_minute=30,
                                   end_hour=14, end_minute=0),
            BlackoutWindowSettings(active=True,  start_hour=17, start_minute=0,
                                   end_hour=21, end_minute=0),
            # active=false ones (don't matter, but kept for transparency)
            BlackoutWindowSettings(active=False, start_hour=0,  start_minute=0,  end_hour=0,  end_minute=5),
            BlackoutWindowSettings(active=False, start_hour=9,  start_minute=0,  end_hour=9,  end_minute=5),
            BlackoutWindowSettings(active=False, start_hour=12, start_minute=0,  end_hour=14, end_minute=0),
            BlackoutWindowSettings(active=False, start_hour=15, start_minute=30, end_hour=15, end_minute=35),
            BlackoutWindowSettings(active=False, start_hour=16, start_minute=30, end_hour=22, end_minute=0),
        ],
        debug=False,
        daily_win_limit_enabled=False,
        daily_win_limit=500.0,
        daily_loss_limit_enabled=False,
        daily_loss_limit=700.0,
        daily_limit_mode="after_close",
    )


def main() -> int:
    print("=" * 100)
    print("V1 MGC ANCHOR — true $DD verification under the PATCHED simulator")
    print("=" * 100)
    print("Preset name: 'New base MomentumChecker — MGC 7m — WINNER (PnL $56.4k / DD $2.43k)'")
    print("Stored metric: total_return=112.7%, max_drawdown=4.74%, win_rate=41.3%, trades=784")
    print()

    s = bench(
        "[V1 MGC anchor — patched]",
        strategy_name="MomentumChecker",
        symbol="MGC",
        interval="7m",
        start="2025-01-07T00:00",
        end="2026-05-15T22:59",
        strategy_params=V1_MGC_PARAMS,
        initial_equity=50_000.0,
        risk_per_trade=0.006,
        max_contracts=20,
        engine_settings=v1_mgc_engine(),
    )
    print()
    print(f"Result:    PnL=${s['net_pnl']:,.0f}  $DD=${s['max_dd_$']:,.0f}  %DD={s['max_dd_%']:.2f}%")
    print(f"Reported:  PnL=$56,400        $DD=$2,430")
    print()
    print(f"Hard ceiling (user): $2,500")
    print(f"Soft target  (user): $2,000")
    if s["max_dd_$"] > 2_500:
        print(f"⚠  V1 anchor's TRUE $DD already exceeds $2,500 — campaign must TIGHTEN, not Pareto-improve.")
    elif s["max_dd_$"] > 2_000:
        print(f"V1 anchor in [$2,000, $2,500] — there's room to maintain PnL with same DD level.")
    else:
        print(f"V1 anchor already under $2,000 soft target — both PnL ↑ and DD ↓ possible.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
