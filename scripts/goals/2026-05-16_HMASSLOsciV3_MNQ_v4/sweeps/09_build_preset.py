"""09 — Build winner preset and confirm metrics one more time.

WINNER: ema=11 BO 11+14 r=0.0036 → $50,770 / $2,268 (margin $232, ratio 22.39).

Steps:
  1. Run the winner one final time to get fresh metrics.
  2. Build preset via _shared/preset.build_preset.
  3. Write to scripts/goals/<slug>/winner_preset.json + insert into data/presets.json.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _campaign as C  # noqa: E402

from scripts.goals._shared.harness import run_backtest, summarize, fmt_summary  # noqa: E402
from scripts.goals._shared.engine_settings import make_engine_settings  # noqa: E402
from scripts.goals._shared.preset import build_preset, write_preset  # noqa: E402


def _window_dict(start_h, end_h):
    return {"start_hour": start_h, "start_minute": 0, "end_hour": end_h, "end_minute": 0}


def main():
    BO_2 = [(11, 12), (14, 15)]
    RISK = 0.0036

    overrides = {"ema_len": 11}  # only one override on top of v3 winner

    print(f"=== 09 BUILD WINNER PRESET ===\n")
    print(f"Config: ema_len=11, BO=11+14, r={RISK}\n")

    es = make_engine_settings(
        C.STRATEGY,
        extra_active_windows=[_window_dict(s, e) for s, e in BO_2],
    )

    params = dict(C.V3_WINNER_PARAMS)
    params.update(overrides)

    result = run_backtest(
        strategy_name=C.STRATEGY,
        symbol=C.SYMBOL,
        interval=C.TF,
        start=C.START,
        end=C.END,
        strategy_params=params,
        initial_equity=C.INITIAL_EQUITY,
        risk_per_trade=RISK,
        max_contracts=C.MAX_CONTRACTS,
        engine_settings=es,
    )
    s = summarize(result)
    print(f"WINNER metrics: {fmt_summary(s)}\n")

    preset = build_preset(
        strategy_name=C.STRATEGY,
        symbol=C.SYMBOL,
        interval=C.TF,
        start=C.START,
        end=C.END,
        initial_equity=C.INITIAL_EQUITY,
        risk_per_trade_decimal=RISK,
        max_contracts=C.MAX_CONTRACTS,
        strategy_param_overrides=params,
        engine_settings=es,
        metrics_summary=s,
    )

    preset_path = Path(__file__).resolve().parents[1] / "winner_preset.json"
    write_preset(preset, preset_path)

    print(f"\n✅ Preset written to {preset_path}")
    print(f"   and inserted into data/presets.json")
    print(f"\nFinal metrics:")
    print(f"  PnL:           ${s['net_pnl']:>10,.2f}")
    print(f"  Max DD:        ${s['max_dd_$']:>10,.2f}")
    print(f"  Margin to cap: ${C.TARGET_MAX_DD - s['max_dd_$']:>10,.2f}")
    print(f"  Trades:         {s['trades']:>10}")
    print(f"  Win rate:       {s['win_rate']:>9.1f}%")
    print(f"  Profit factor:  {s['profit_factor']}")
    return s


if __name__ == "__main__":
    main()
