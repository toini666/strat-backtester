"""Phase 3 — combo final des hypothèses KEEP.

S'exécute après `01_pairs.py`. Active toutes les hypothèses KEEP simultanément
et compare aux baselines. Si bat les baselines, on builde un preset V4 par
asset (via `_shared/preset.py::build_preset` + `write_preset`).
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "phase2_hypotheses"))

from scripts.goals._shared.harness import run_backtest, summarize  # noqa: E402
from scripts.goals._shared.preset import build_preset, write_preset, engine_from_dict  # noqa: E402
from _shared import BASELINES, BASELINE_METRICS, load_preset, preset_to_runargs, print_ab_header, print_ab_row  # noqa: E402

# === MAJ après Phase 2/3 ===================================================
# Only MGC has a winning combo. MNQ: no hypothesis improved P/DD ratio.
WINNER_PARAMS: dict[str, dict] = {
    "MGC_v3": {
        "lab_entry_blocked_hours": (22, 20),
        "lab_disable_canal_exit_from_hour": 21,
    },
}
# ==========================================================================

OUTPUT_DIR = Path(__file__).resolve().parents[1]


def main():
    if not WINNER_PARAMS:
        print("⚠️  WINNER_PARAMS is empty — fill in after Phase 2 verdicts.")
        return
    print_ab_header("Phase 3 — winner combo (all KEEP active)")
    for label, path in BASELINES.items():
        if label not in WINNER_PARAMS:
            print(f"   [{label}] skipped (no winner params).")
            continue
        preset = load_preset(path)
        kwargs = preset_to_runargs(preset, strategy_name="HMASSLOsciV3Labv1")
        baseline = summarize(run_backtest(**kwargs))
        base_pnl, base_dd, base_n = baseline["net_pnl"], baseline["max_dd_$"], baseline["trades"]
        print_ab_row(label, "OFF (baseline)", base_pnl, base_dd, base_n, base_pnl, base_dd, base_n)

        # Combo
        combo_kwargs = dict(kwargs)
        combo_kwargs["strategy_params"] = {**kwargs["strategy_params"], **WINNER_PARAMS[label]}
        r = summarize(run_backtest(**combo_kwargs))
        print_ab_row(label, "COMBO winner", r["net_pnl"], r["max_dd_$"], r["trades"], base_pnl, base_dd, base_n)

        # Compose preset V4 if better
        improved = (r["net_pnl"] > base_pnl - 50) and (
            r["net_pnl"] / r["max_dd_$"] > base_pnl / base_dd
        )
        if improved:
            symbol = preset["symbol"]
            asset_tag = symbol  # e.g. "MNQ"
            preset_overrides = {**preset["params"], **WINNER_PARAMS[label]}
            preset_overrides.pop("tick_size", None)
            v4 = build_preset(
                strategy_name="HMASSLOsciV3Labv1",
                symbol=preset["symbol"],
                interval=preset["interval"],
                start=preset["startDatetime"],
                end=preset["endDatetime"],
                initial_equity=preset["initialEquity"],
                risk_per_trade_decimal=preset["riskPerTrade"] / 100.0,
                max_contracts=preset["maxContracts"],
                strategy_param_overrides=preset_overrides,
                engine_settings=engine_from_dict(preset["engineSettings"]),
                metrics_summary=r,
                name=(
                    f"[Auto] HMASSLOsciV3Labv1 — {symbol} {preset['interval']} v4 "
                    f"(PnL ${r['net_pnl']/1000:.1f}k / DD ${r['max_dd_$']/1000:.1f}k)"
                ),
            )
            out = OUTPUT_DIR / f"winner_v4_{asset_tag}.json"
            write_preset(v4, out)
            print(f"   → wrote {out}")
        else:
            print(f"   ❌ {label}: combo did not strictly improve P/DD vs baseline — preset NOT written.")


if __name__ == "__main__":
    main()
