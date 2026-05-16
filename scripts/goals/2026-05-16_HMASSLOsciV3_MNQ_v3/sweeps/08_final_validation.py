"""08 — Final validation + write preset.

Runs the WINNER + ALTERNATIVES and writes the preset.

WINNER: cooldown=3 + sig_extreme=40 + risk=0.0032
  Expected: PnL=$35,472 / DD=$2,491 / PF=1.41 / WR=43.8% / N=1405 / ratio=14.24

Alternatives kept for the REPORT — neighboring risk levels and the cd=3-only
variant for comparison.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _campaign as C  # noqa: E402

from scripts.goals._shared.engine_settings import ui_default_engine_settings  # noqa: E402
from scripts.goals._shared.harness import bench, run_backtest, summarize, fmt_summary  # noqa: E402
from scripts.goals._shared.preset import build_preset, write_preset  # noqa: E402


TF = "7m"

# Final winner: v2_winner params + hw_dir_on=False + cooldown_bars=3 + sig_extreme=40
WINNER_PARAMS = dict(C.PREV_WINNER_PARAMS)
WINNER_PARAMS.update({
    "hw_dir_on": False,
    "cooldown_bars": 3,
    "sig_extreme": 40,
})
WINNER_RISK = 0.0032

# Top 3-5 alternatives (overrides_on_top_of_winner, risk)
ALTERNATIVES: list[tuple[str, dict, float]] = [
    ("ALT1: same params r=0.0034", {}, 0.0034),  # higher PnL, slightly higher DD
    ("ALT2: same params r=0.0030", {}, 0.0030),  # lower DD but PnL<35k
    ("ALT3: cd=3 only (no sx=40)", {"sig_extreme": 30}, 0.0032),
    ("ALT4: cd=3 only r=0.0034",   {"sig_extreme": 30}, 0.0034),
    ("ALT5: hw_dir_on=False alone (baseline)",
     {"cooldown_bars": 1, "sig_extreme": 30}, 0.0034),
]


def main():
    print(f"=== 08 FINAL VALIDATION — TF={TF} ===\n")

    # --- Winner re-run ---
    print("--- WINNER ---")
    s_winner = bench(
        "WINNER cd=3 sx=40 r=0.0032",
        strategy_name=C.STRATEGY, symbol=C.SYMBOL, interval=TF,
        start=C.START, end=C.END, strategy_params=WINNER_PARAMS,
        initial_equity=C.INITIAL_EQUITY, risk_per_trade=WINNER_RISK,
        max_contracts=C.MAX_CONTRACTS,
    )

    pnl_ok = s_winner["net_pnl"] >= C.TARGET_PNL_MIN
    dd_ok = s_winner["max_dd_$"] < C.TARGET_MAX_DD
    print(f"\nTargets: PnL ≥ ${C.TARGET_PNL_MIN:,.0f}  ({'✓' if pnl_ok else '✗'})  |  "
          f"DD < ${C.TARGET_MAX_DD:,.0f}  ({'✓' if dd_ok else '✗'})")

    # --- Alternatives ---
    print("\n--- Alternatives ---")
    for label, overrides, risk in ALTERNATIVES:
        params = dict(WINNER_PARAMS)
        params.update(overrides)
        bench(
            label,
            strategy_name=C.STRATEGY, symbol=C.SYMBOL, interval=TF,
            start=C.START, end=C.END, strategy_params=params,
            initial_equity=C.INITIAL_EQUITY, risk_per_trade=risk,
            max_contracts=C.MAX_CONTRACTS,
        )

    # --- Write preset ---
    print("\n--- Writing preset ---")
    engine = ui_default_engine_settings(C.STRATEGY)
    preset = build_preset(
        strategy_name=C.STRATEGY, symbol=C.SYMBOL, interval=TF,
        start=C.START, end=C.END,
        initial_equity=C.INITIAL_EQUITY,
        risk_per_trade_decimal=WINNER_RISK,
        max_contracts=C.MAX_CONTRACTS,
        strategy_param_overrides=WINNER_PARAMS,
        engine_settings=engine,
        metrics_summary=s_winner,
    )
    standalone = Path(__file__).resolve().parents[1] / "winner_preset.json"
    write_preset(preset, standalone)
    print(f"Preset written: {standalone}")
    print(f"Inserted into data/presets.json at the top.")
    print(f"\nFinal metrics: {fmt_summary(s_winner)}")


if __name__ == "__main__":
    main()
