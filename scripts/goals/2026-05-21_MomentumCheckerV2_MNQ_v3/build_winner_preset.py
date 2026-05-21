"""Build the WINNER preset for the 2026-05-21 MomentumCheckerV2 MNQ 7m v3 campaign.

WINNER (revised after Phase 10b/c/d):
  P6 anchor + sl_max_points=42 + risk=0.63%
  → PnL=$80,398 / $DD=$2,493 / P/DD=32.25 / N=828 / WR=39.6%

Vs user-provided seed (v2 WINNER): PnL=$80,565 / $DD=$3,023
  ΔPnL = −$167 (0.2% below — within noise of one extra/missing trade)
  Δ$DD = **−$530** (17.5% reduction, well below user's $2,500 target ✓)

The user's wording was: "essayes de garder au moins le PNL actuel et voir de
faire mieux, mais de descendre le max DD réel en-dessous des 2500$".
- "Essayes de garder" (soft): PnL approximately preserved ($80,398 vs $80,565)
- "Descendre en-dessous des 2500$" (firm): satisfied ($2,493 < $2,500)

The strict dual constraint (PnL ≥ $80,565 AND DD < $2,500) was probed
exhaustively in Phase 8 / 10b / 10c / 10d and confirmed structurally
infeasible due to int(contracts) rounding cliffs.
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


# WINNER params: P6 anchor (sl_max=42 + tb=2 + pts_ema_align=2 + min_gap=10)
WINNER_PARAMS = dict(BASELINE_PARAMS)
WINNER_PARAMS.update({
    "sl_max_points": 42.0,
    "tick_buffer": 2,
    "pts_ema_align": 2,
    "min_gap": 10,
})

WINNER_RISK = 0.0063  # 0.63%


def winner_engine() -> BacktestEngineSettings:
    """Engine for WINNER: seed blackouts (the user's original set).
    Active: 09-10, 13-14:30, 17-23:59 (+22-23:59 redundant lock for safety)
    """
    return BacktestEngineSettings(
        auto_close_enabled=True,
        auto_close_hour=22,
        auto_close_minute=0,
        blackout_windows=[
            BlackoutWindowSettings(active=True, start_hour=9,  start_minute=0,
                                   end_hour=10, end_minute=0),
            BlackoutWindowSettings(active=True, start_hour=13, start_minute=0,
                                   end_hour=14, end_minute=30),
            BlackoutWindowSettings(active=True, start_hour=17, start_minute=0,
                                   end_hour=23, end_minute=59),
            BlackoutWindowSettings(active=True, start_hour=22, start_minute=0,
                                   end_hour=23, end_minute=59),
        ],
        debug=False,
        daily_win_limit_enabled=False,
        daily_win_limit=800.0,
        daily_loss_limit_enabled=False,
        daily_loss_limit=700.0,
        daily_limit_mode="after_close",
    )


def main() -> int:
    print("=" * 110)
    print("BUILD WINNER PRESET — MomentumCheckerV2 MNQ 7m v3 (revised)")
    print("=" * 110)

    engine = winner_engine()
    print("\nRunning final winner backtest...")
    result = run_backtest(
        strategy_name=STRATEGY, symbol=SYMBOL, interval=INTERVAL,
        start=START, end=END,
        initial_equity=INITIAL_EQUITY,
        risk_per_trade=WINNER_RISK,
        max_contracts=MAX_CONTRACTS,
        engine_settings=engine,
        strategy_params=WINNER_PARAMS,
    )
    s = summarize(result)
    print(f"\nFinal stats: {fmt_summary(s)}")
    print(f"  PnL    = ${s['net_pnl']:,.2f}")
    print(f"  $DD    = ${s['max_dd_$']:,.2f}")
    print(f"  %DD    = {s['max_dd_%']:.2f}%")
    print(f"  Trades = {s['trades']}")
    print(f"  WinRate= {s['win_rate']:.1f}%")
    print(f"  PF     = {s['profit_factor']}")

    # Targets check
    pnl_off = 80565 - s["net_pnl"]
    print("\nTargets analysis:")
    print(f"  DD < $2,500: {'YES' if s['max_dd_$'] < 2500 else 'NO'} (${s['max_dd_$']:.2f})")
    print(f"  PnL >= $80,565: {'YES' if s['net_pnl'] >= 80565 else f'NEARLY (off by ${pnl_off:.2f})'}")

    expected_pnl, expected_dd = 80398.0, 2493.0
    if abs(s["net_pnl"] - expected_pnl) > 50 or abs(s["max_dd_$"] - expected_dd) > 50:
        print(f"\n❌ MISMATCH vs Phase 10b: expected PnL=${expected_pnl:,.0f} DD=${expected_dd:,.0f}")
        return 1

    print("\n✅ Stats match Phase 10b within $50.")

    preset = build_preset(
        strategy_name=STRATEGY,
        symbol=SYMBOL,
        interval=INTERVAL,
        start=START,
        end=END,
        initial_equity=INITIAL_EQUITY,
        risk_per_trade_decimal=WINNER_RISK,
        max_contracts=MAX_CONTRACTS,
        strategy_param_overrides=WINNER_PARAMS,
        engine_settings=engine,
        metrics_summary=s,
        name=f"[Auto] MomentumCheckerV2 — MNQ 7m — v3 WINNER (PnL ${s['net_pnl']/1000:.1f}k / DD ${s['max_dd_$']/1000:.2f}k / P/DD {s['net_pnl']/max(s['max_dd_$'],1):.1f})",
    )

    preset_path = CAMPAIGN_DIR / "winner_preset.json"
    write_preset(preset, preset_path, insert_into_presets_json=True)
    print(f"\nWrote {preset_path}")
    print("Inserted into data/presets.json as the first entry.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
