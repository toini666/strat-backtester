"""Phase 9 — Final validation: build the winner preset, replay it, verify.

Winner (from Phase 8b):
  • Strategy:   HMASSLOsciV4
  • Symbol/TF:  MNQ / 7m
  • Period:     2025-01-06 → 2026-05-15
  • Risk:       0.495% (0.00495 decimal)
  • Strategy params: V3-migrated baseline + hw_extreme_on=False + sig_extreme_on=False
  • Blackouts:  baseline (08-09, 11-12, 12-13, 14-15, 22:00-23:59) + NEW 06-08
  • Daily limit: after_close loss=$700

Float-precision note: 0.00495 → stored 0.495 → recovered 0.004949999... causes a
2-trade / $53 drift through position-sizing × daily-limit propagation. The
*replay* metrics are the canonical winner numbers (= what the user sees when
they load the preset from the UI).
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from scripts.goals._shared.engine_settings import make_engine_settings
from scripts.goals._shared.harness import bench, run_backtest, summarize, fmt_summary
from scripts.goals._shared.preset import build_preset, replay_preset, verify_preset, write_preset

from _campaign import (
    BASELINE_ACTIVE_BLACKOUTS,
    BASELINE_V4_PARAMS,
    END,
    INITIAL_EQUITY,
    INTERVAL,
    MAX_CONTRACTS,
    START,
    STRATEGY,
    SYMBOL,
)


EXTRA_06_08 = {"start_hour": 6, "start_minute": 0, "end_hour": 8, "end_minute": 0}
WINNER_RISK = 0.00495
WINNER_LOSS_LIMIT = 700.0

WINNER_PARAMS = dict(BASELINE_V4_PARAMS)
WINNER_PARAMS["hw_extreme_on"] = False
WINNER_PARAMS["sig_extreme_on"] = False


def _engine():
    return make_engine_settings(
        STRATEGY,
        extra_active_windows=list(BASELINE_ACTIVE_BLACKOUTS) + [EXTRA_06_08],
        daily_loss_limit=WINNER_LOSS_LIMIT,
        daily_limit_mode="after_close",
    )


def _run(label, *, params=None, risk=None, engine=None):
    return bench(
        label,
        strategy_name=STRATEGY,
        symbol=SYMBOL,
        interval=INTERVAL,
        start=START,
        end=END,
        strategy_params=params or WINNER_PARAMS,
        initial_equity=INITIAL_EQUITY,
        risk_per_trade=risk if risk is not None else WINNER_RISK,
        max_contracts=MAX_CONTRACTS,
        engine_settings=engine or _engine(),
    )


def main() -> int:
    print("=" * 120)
    print("PHASE 9 — Final validation")
    print("=" * 120)

    # Run the winner direct.
    res_direct = run_backtest(
        strategy_name=STRATEGY,
        symbol=SYMBOL,
        interval=INTERVAL,
        start=START,
        end=END,
        strategy_params=WINNER_PARAMS,
        initial_equity=INITIAL_EQUITY,
        risk_per_trade=WINNER_RISK,
        max_contracts=MAX_CONTRACTS,
        engine_settings=_engine(),
    )
    s_direct = summarize(res_direct)
    print(f"  WINNER (direct call)   {fmt_summary(s_direct)}\n")

    print("-" * 120)
    print("Alternatives (replay)")
    print("-" * 120)
    _run("ALT1 risk=0.500% no limit",
         risk=0.005,
         engine=make_engine_settings(STRATEGY,
                                     extra_active_windows=list(BASELINE_ACTIVE_BLACKOUTS) + [EXTRA_06_08]))
    _run("ALT2 risk=0.490% +L700", risk=0.0049)
    _run("ALT3 V3-strict +H=06-08 risk=0.495% +L700",
         params=BASELINE_V4_PARAMS, risk=0.00495)
    _run("ALT4 risk=0.500% +L700", risk=0.005)
    _run("ALT5 baseline blackouts + relax + risk=0.495% + L700",
         engine=make_engine_settings(STRATEGY,
                                     extra_active_windows=BASELINE_ACTIVE_BLACKOUTS,
                                     daily_loss_limit=WINNER_LOSS_LIMIT,
                                     daily_limit_mode="after_close"),
         risk=0.00495)

    # Build preset using the DIRECT metrics first (for the name placeholder),
    # then replay to get the canonical numbers, then re-build with those.
    print()
    print("-" * 120)
    print("Building winner_preset.json …")
    preset_path = Path(__file__).resolve().parents[1] / "winner_preset.json"
    placeholder = build_preset(
        strategy_name=STRATEGY, symbol=SYMBOL, interval=INTERVAL,
        start=START, end=END,
        initial_equity=INITIAL_EQUITY,
        risk_per_trade_decimal=WINNER_RISK,
        max_contracts=MAX_CONTRACTS,
        strategy_param_overrides=WINNER_PARAMS,
        engine_settings=_engine(),
        metrics_summary=s_direct,
        name="[temp]",
    )
    write_preset(placeholder, preset_path, insert_into_presets_json=False)

    s_canonical = replay_preset(preset_path)
    print(f"  CANONICAL replay       {fmt_summary(s_canonical)}\n")

    # Now re-build the preset with the canonical (replay) metrics in name + metrics.
    name = (f"[WIN MNQ V4] HMASSLOsciV4 — MNQ {INTERVAL} — V4 "
            f"(PnL ${s_canonical['net_pnl']/1000:.1f}k / DD ${s_canonical['max_dd_$']/1000:.2f}k)")
    final_preset = build_preset(
        strategy_name=STRATEGY, symbol=SYMBOL, interval=INTERVAL,
        start=START, end=END,
        initial_equity=INITIAL_EQUITY,
        risk_per_trade_decimal=WINNER_RISK,
        max_contracts=MAX_CONTRACTS,
        strategy_param_overrides=WINNER_PARAMS,
        engine_settings=_engine(),
        metrics_summary=s_canonical,
        name=name,
    )
    # preserve placeholder UUID for stability
    final_preset["id"] = placeholder["id"]
    write_preset(final_preset, preset_path, insert_into_presets_json=True)
    print(f"  Wrote {preset_path}")
    print(f"  Inserted into data/presets.json (top of list)")
    print(f"  Direct vs canonical PnL drift: ${s_direct['net_pnl'] - s_canonical['net_pnl']:+.2f} "
          f"(float-precision artifact on riskPerTrade serialization)")

    # Final verify using canonical numbers.
    print()
    print("-" * 120)
    print("Verifying preset replay …")
    expected = {
        "net_pnl": round(s_canonical["net_pnl"]),
        "max_dd_$": round(s_canonical["max_dd_$"]),
        "trades": s_canonical["trades"],
        "win_rate": s_canonical["win_rate"],
        "profit_factor": s_canonical["profit_factor"],
    }
    ok = verify_preset(preset_path, expected, pnl_tolerance=5.0, dd_tolerance=5.0)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
