"""Constantes et helpers partagés par tous les sweeps de Phase 2."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

ROOT = Path(__file__).resolve().parents[4]

# Chaque baseline = chemin absolu vers un winner preset V3.
BASELINES = {
    "MNQ_v5": ROOT / "scripts/goals/2026-05-17_HMASSLOsciV3_MNQ_v5/winner_preset.json",
    "MGC_v3": ROOT / "scripts/goals/2026-05-17_HMASSLOsciV3_MGC_v3/winner_preset.json",
}

# Métriques publiées dans les REPORT.md des baselines.
BASELINE_METRICS = {
    "MNQ_v5": {"pnl": 68_765.0, "dd": 1_579.0, "trades": 1_241, "wr": 48.3, "pf": 1.70},
    "MGC_v3": {"pnl": 44_692.0, "dd": 1_944.0, "trades": 865, "wr": 55.1, "pf": 1.66},
}


def load_preset(path: Path) -> Dict[str, Any]:
    """Load a baseline preset JSON dict."""
    return json.loads(Path(path).read_text())


def preset_to_runargs(preset: Dict[str, Any], strategy_name: str | None = None) -> Dict[str, Any]:
    """Convert a UI preset to kwargs for run_backtest()."""
    from scripts.goals._shared.preset import engine_from_dict

    engine = engine_from_dict(preset["engineSettings"])
    overrides = {k: v for k, v in preset["params"].items() if k != "tick_size"}
    return dict(
        strategy_name=strategy_name or preset["strategyName"],
        symbol=preset["symbol"],
        interval=preset["interval"],
        start=preset["startDatetime"],
        end=preset["endDatetime"],
        strategy_params=overrides,
        initial_equity=preset["initialEquity"],
        risk_per_trade=preset["riskPerTrade"] / 100.0,
        max_contracts=preset["maxContracts"],
        engine_settings=engine,
    )


def print_ab_header(hypothesis: str) -> None:
    print()
    print(f"=== Hypothesis: {hypothesis} ===")
    print(
        f"{'Preset':<10s} | {'Variant':<32s} | "
        f"{'PnL':>9s} | {'DD':>7s} | {'N':>5s} | "
        f"{'ΔPnL':>9s} | {'ΔDD':>7s} | {'ΔN':>5s} | "
        f"{'P/DD':>6s} | ΔP/DD"
    )


def print_ab_row(
    preset_label: str,
    variant_label: str,
    on_pnl: float,
    on_dd: float,
    on_n: int,
    base_pnl: float,
    base_dd: float,
    base_n: int,
) -> None:
    dpnl = on_pnl - base_pnl
    ddd = on_dd - base_dd
    dn = on_n - base_n
    base_pdd = base_pnl / base_dd if base_dd else 0.0
    on_pdd = on_pnl / on_dd if on_dd else 0.0
    print(
        f"{preset_label:<10s} | {variant_label:<32s} | "
        f"${on_pnl:>8,.0f} | ${on_dd:>6,.0f} | {on_n:>5d} | "
        f"{dpnl:>+9,.0f} | {ddd:>+7,.0f} | {dn:>+5d} | "
        f"{on_pdd:>6.2f} | {(on_pdd-base_pdd):+5.2f}"
    )


def run_sweep(
    hypothesis_name: str,
    param_key: str,
    off_value: Any,
    on_values: list,
    extra_overrides: Dict[str, Any] | None = None,
):
    """A/B sweep loop : for each preset, run Lab(OFF) + Lab(ON=v) for each v.

    OFF replay uses Lab(defaults) — already proven equivalent to V3 by sanity.
    Returns a list of dict rows: {preset, variant, pnl, dd, n, …}.
    """
    from scripts.goals._shared.harness import run_backtest, summarize  # noqa: E402

    print_ab_header(hypothesis_name)
    rows = []
    for label, path in BASELINES.items():
        preset = load_preset(path)
        # Lab(OFF) — should match the baseline exactly
        kwargs = preset_to_runargs(preset, strategy_name="HMASSLOsciV3Labv1")
        if extra_overrides:
            kwargs["strategy_params"] = {**kwargs["strategy_params"], **extra_overrides}
        # OFF
        kwargs_off = dict(kwargs)
        kwargs_off["strategy_params"] = {**kwargs["strategy_params"], param_key: off_value}
        r_off = summarize(run_backtest(**kwargs_off))
        base_pnl, base_dd, base_n = r_off["net_pnl"], r_off["max_dd_$"], r_off["trades"]
        rows.append({"preset": label, "variant": "OFF", "value": off_value,
                     "pnl": base_pnl, "dd": base_dd, "n": base_n})
        # Print OFF row (no delta needed but for layout)
        print_ab_row(label, f"OFF (={off_value})", base_pnl, base_dd, base_n,
                     base_pnl, base_dd, base_n)
        # ON sweep
        for v in on_values:
            kwargs_on = dict(kwargs)
            kwargs_on["strategy_params"] = {**kwargs["strategy_params"], param_key: v}
            r_on = summarize(run_backtest(**kwargs_on))
            rows.append({"preset": label, "variant": f"ON={v}", "value": v,
                         "pnl": r_on["net_pnl"], "dd": r_on["max_dd_$"], "n": r_on["trades"]})
            print_ab_row(label, f"ON ({param_key}={v})",
                         r_on["net_pnl"], r_on["max_dd_$"], r_on["trades"],
                         base_pnl, base_dd, base_n)
        print()
    return rows
