"""Common runner for hypothesis sweeps.

Each sweep file defines:
  - HYPOTHESIS_NAME, HYPOTHESIS_DESC, LEVER ("EX"|"PT"), ANGLE ("W"|"L"|"W+L")
  - VARIANTS: list of dicts {label, overrides}  → ON runs (label = "OFF" → baseline)

This runner handles loading the preset, swapping strategy to Lab, executing
A/B runs on each baseline, and printing the comparison table.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.goals._shared.harness import run_backtest, summarize  # noqa: E402
from scripts.goals._shared.preset import engine_from_dict  # noqa: E402

from _shared import BASELINES, LAB_STRATEGY_NAME, load_preset, strategy_params, print_ab_header, print_ab_row


def run_one(preset: Dict[str, Any], lab_overrides: Dict[str, Any]) -> Dict[str, Any]:
    engine = engine_from_dict(preset["engineSettings"])
    p = strategy_params(preset, lab_overrides)
    res = run_backtest(
        strategy_name=LAB_STRATEGY_NAME,
        symbol=preset["symbol"],
        interval=preset["interval"],
        start=preset["startDatetime"],
        end=preset["endDatetime"],
        strategy_params=p,
        initial_equity=preset["initialEquity"],
        risk_per_trade=preset["riskPerTrade"] / 100.0,
        max_contracts=preset["maxContracts"],
        engine_settings=engine,
    )
    return summarize(res)


def sweep(name: str, description: str, lever: str, angle: str,
          variants: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Run OFF baseline + each ON variant on each baseline. Return aggregated table."""
    print(f"\n{'='*100}")
    print(f"  Hypothesis: {name}   |  Lever: {lever}  |  Angle: {angle}")
    print(f"  {description}")
    print(f"{'='*100}")

    all_rows: List[Dict[str, Any]] = []
    for asset, path in BASELINES.items():
        preset = load_preset(path)
        # OFF run = Lab with no flag overrides (= V3 equivalent already verified by sanity)
        off = run_one(preset, {})
        print_ab_header(f"{name} on {asset}")
        for variant in variants:
            on = run_one(preset, variant["overrides"])
            row = print_ab_row(f"{asset}/{variant['label']}", off, on)
            row["variant"] = variant["label"]
            row["asset"] = asset
            all_rows.append(row)
    return {
        "name": name,
        "description": description,
        "lever": lever,
        "angle": angle,
        "rows": all_rows,
    }


def save_result(name: str, payload: Dict[str, Any]) -> None:
    out = Path(__file__).resolve().parent / "logs" / f"{name}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2))
    print(f"\n  → results dumped to {out.relative_to(ROOT)}")
