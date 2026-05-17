"""00_sanity_lab_equals_v3 — Lab(defaults) must reproduce V3 baselines exactly.

Loads each reference preset, swaps strategyName → HMASSLOsciV3LabExitV1
with ALL Lab flags at their default values, and verifies that the resulting
backtest matches the original V3 metrics to the cent.

Also captures the baseline metrics into a JSON cache that downstream sweeps
read instead of re-replaying.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from scripts.goals._shared.harness import run_backtest, summarize, fmt_summary
from scripts.goals._shared.preset import engine_from_dict
from _shared import BASELINES, LAB_STRATEGY_NAME, load_preset, strategy_params


PNL_TOL = 0.01
DD_TOL = 0.01

CACHE_FILE = Path(__file__).resolve().parent / "_baseline_cache.json"


def run_with_strategy(preset: dict, strategy_name: str) -> dict:
    engine = engine_from_dict(preset["engineSettings"])
    p = strategy_params(preset)
    res = run_backtest(
        strategy_name=strategy_name,
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


def main():
    print(f"{'='*80}\n SANITY: Lab(defaults) == V3 (tolerance ${PNL_TOL} / ${DD_TOL})\n{'='*80}")
    all_ok = True
    cache = {}
    for name, path in BASELINES.items():
        preset = load_preset(path)
        v3 = run_with_strategy(preset, "HMASSLOsciV3")
        lab = run_with_strategy(preset, LAB_STRATEGY_NAME)
        print(f"\n[{name}]  ({path.relative_to(ROOT)})")
        print(f"  V3:  {fmt_summary(v3)}")
        print(f"  Lab: {fmt_summary(lab)}")
        dpnl = abs(lab["net_pnl"] - v3["net_pnl"])
        ddd = abs(lab["max_dd_$"] - v3["max_dd_$"])
        ok = dpnl < PNL_TOL and ddd < DD_TOL and lab["trades"] == v3["trades"]
        print(f"  Δ:   |PnL|=${dpnl:.4f}  |DD|=${ddd:.4f}  N_diff={lab['trades']-v3['trades']}")
        if ok:
            print(f"  ✅ MATCH")
        else:
            print(f"  ❌ MISMATCH — Lab strategy is broken, do NOT proceed.")
            all_ok = False
        cache[name] = {
            "v3": v3,
            "preset_path": str(path.relative_to(ROOT)),
        }
    CACHE_FILE.write_text(json.dumps(cache, indent=2))
    print(f"\n{'='*80}")
    print(f"  Baseline cache → {CACHE_FILE.relative_to(ROOT)}")
    print(f"  Overall: {'✅ ALL MATCH' if all_ok else '❌ FAILED'}")
    print(f"{'='*80}")
    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
