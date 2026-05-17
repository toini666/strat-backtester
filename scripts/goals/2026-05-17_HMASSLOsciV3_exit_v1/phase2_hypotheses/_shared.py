"""Constants and helpers shared across hypothesis sweeps."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

ROOT = Path(__file__).resolve().parents[4]

# Each baseline = absolute path to a winner preset of the V3 reference.
BASELINES: Dict[str, Path] = {
    "MNQ_v5": ROOT / "scripts/goals/2026-05-17_HMASSLOsciV3_MNQ_v5/winner_preset.json",
    "MGC_v3": ROOT / "scripts/goals/2026-05-17_HMASSLOsciV3_MGC_v3/winner_preset.json",
}

# Reference PnL/DD from each baseline (filled at sanity-check time once
# replay_preset has been run; treat as cache for downstream sweeps to print
# baseline deltas without re-running).
BASELINE_METRICS: Dict[str, Dict[str, float]] = {
    # Populated at runtime by 00_sanity_lab_equals_v3.py — must reproduce
    # the published REPORT.md figures to the cent.
}

LAB_STRATEGY_NAME = "HMASSLOsciV3LabExitV1"


def load_preset(path: Path) -> Dict[str, Any]:
    with open(path) as f:
        return json.load(f)


def swap_strategy_name(preset: Dict[str, Any], new_name: str) -> Dict[str, Any]:
    """Return a *deep enough* copy of the preset with strategyName replaced."""
    out = dict(preset)
    out["strategyName"] = new_name
    return out


def strategy_params(preset: Dict[str, Any], overrides: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """Return the preset's strategy params merged with overrides, sans tick_size."""
    p = {k: v for k, v in preset["params"].items() if k != "tick_size"}
    if overrides:
        p.update(overrides)
    return p


def fmt_money(x: float) -> str:
    return f"${x:>10,.0f}"


def print_ab_header(name: str) -> None:
    print(f"\n=== Hypothesis: {name} ===")
    print(f"{'Preset':<14s} | {'OFF PnL':>10s} | {'OFF DD':>8s} | "
          f"{'ON PnL':>10s} | {'ON DD':>8s} | "
          f"{'ΔPnL':>9s} | {'ΔDD':>7s} | {'ΔP/DD':>6s} | "
          f"{'ΔWR':>6s} | {'OFF N':>5s} | {'ON N':>5s}")


def print_ab_row(label: str, off: Dict[str, Any], on: Dict[str, Any]) -> Dict[str, Any]:
    """Print one A/B row + return deltas dict for downstream collation."""
    base_pnl, base_dd = off["net_pnl"], off["max_dd_$"]
    on_pnl, on_dd = on["net_pnl"], on["max_dd_$"]
    base_pdd = base_pnl / base_dd if base_dd else 0
    on_pdd = on_pnl / on_dd if on_dd else 0
    dpnl = on_pnl - base_pnl
    ddd = on_dd - base_dd
    dpdd = on_pdd - base_pdd
    dwr = on["win_rate"] - off["win_rate"]
    print(f"{label:<14s} | {fmt_money(base_pnl)} | ${base_dd:>6,.0f} | "
          f"{fmt_money(on_pnl)} | ${on_dd:>6,.0f} | "
          f"{dpnl:+9,.0f} | {ddd:+7,.0f} | {dpdd:+6.2f} | "
          f"{dwr:+5.1f}% | {off['trades']:>5d} | {on['trades']:>5d}")
    return {
        "preset": label,
        "off_pnl": base_pnl, "off_dd": base_dd, "off_trades": off["trades"],
        "on_pnl": on_pnl, "on_dd": on_dd, "on_trades": on["trades"],
        "dpnl": dpnl, "ddd": ddd, "dpdd": dpdd, "dwr": dwr,
    }
