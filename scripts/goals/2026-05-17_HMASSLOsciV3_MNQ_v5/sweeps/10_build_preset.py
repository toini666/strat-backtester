"""10 — Build the winner preset.

WINNER: BASE_A (V4 BO + H=08+12) + mf_length=31 + mf_smooth=7 + r=0.0048.
Metrics: $68,765 PnL / $1,579 DD / margin $421 / ratio 43.55 / N=1241 / WR=48.3% / PF=1.70.

Diff vs V4:
  - mf_length:   25 → 31   (sweep 06/07/08 breakthrough)
  - mf_smooth:    6 →  7   (sweep 07 booster)
  - blackouts:   +H=08 (8-9) + H=12 (12-13) (sweep 03 breakthrough)
  - risk:    0.0036 → 0.0048 (sweep 09 — integer-contract DD non-monotone)
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _campaign as C  # noqa: E402

from scripts.goals._shared.harness import run_backtest, summarize, fmt_summary  # noqa: E402
from scripts.goals._shared.engine_settings import make_engine_settings  # noqa: E402
from scripts.goals._shared.preset import build_preset, write_preset  # noqa: E402


def main():
    print("=== 10 — BUILD WINNER PRESET ===\n")

    BASE_A = [(11, 12), (14, 15), (8, 9), (12, 13)]
    RISK = 0.0048
    overrides = {
        "mf_length": 31,
        "mf_smooth": 7,
    }

    print(f"Config:")
    print(f"  - V4 base params + mf_length=31, mf_smooth=7")
    print(f"  - Blackouts: 11-12, 14-15, 8-9, 12-13 (active) + 22-23:59 (UI default)")
    print(f"  - Risk: r={RISK}")
    print(f"  - Auto-close: 22:00 (CME daily close)\n")

    es = make_engine_settings(
        C.STRATEGY,
        extra_active_windows=[C.window(s, e) for s, e in BASE_A],
    )

    params = dict(C.V4_WINNER_PARAMS)
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
    print(f"  Ratio:          {s['net_pnl']/s['max_dd_$']:>10.2f}")
    print(f"  Trades:         {s['trades']:>10}")
    print(f"  Win rate:       {s['win_rate']:>9.1f}%")
    print(f"  Profit factor:  {s['profit_factor']}")
    return s


if __name__ == "__main__":
    main()
