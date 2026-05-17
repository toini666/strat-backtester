"""Phase 4 — walk-forward validation.

Split each preset's period 50/50 (train / test) and re-measure the Phase 2
hypothesis that showed the least-bad signal (H6 partial at fast cross 25%).
If the PnL delta sign flips between halves, the Phase 2 signal is noise.

Also re-confirms the V3 baselines on each fold (the campaign deliverable
should remain reproducible regardless of period).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent / "phase2_hypotheses"))

from scripts.goals._shared.harness import run_backtest, summarize  # noqa: E402
from scripts.goals._shared.preset import engine_from_dict  # noqa: E402

from _shared import BASELINES, LAB_STRATEGY_NAME, load_preset, strategy_params  # noqa: E402


def midpoint_date(start: str, end: str) -> str:
    s = datetime.fromisoformat(start)
    e = datetime.fromisoformat(end)
    mid = s + (e - s) / 2
    return mid.strftime("%Y-%m-%dT%H:%M")


def run_one(preset, lab_overrides, start, end):
    engine = engine_from_dict(preset["engineSettings"])
    p = strategy_params(preset, lab_overrides)
    res = run_backtest(
        strategy_name=LAB_STRATEGY_NAME,
        symbol=preset["symbol"],
        interval=preset["interval"],
        start=start,
        end=end,
        strategy_params=p,
        initial_equity=preset["initialEquity"],
        risk_per_trade=preset["riskPerTrade"] / 100.0,
        max_contracts=preset["maxContracts"],
        engine_settings=engine,
    )
    return summarize(res)


def main():
    overrides_to_test = [
        {"label": "OFF (V3 baseline)", "overrides": {}},
        {"label": "H6_25 fast_cross partial", "overrides": {"lab_pt_on_fast_cross_pct": 25.0}},
        {"label": "H6_10 fast_cross partial", "overrides": {"lab_pt_on_fast_cross_pct": 10.0}},
    ]
    results = {}
    for asset, path in BASELINES.items():
        preset = load_preset(path)
        full_start = preset["startDatetime"]
        full_end = preset["endDatetime"]
        mid = midpoint_date(full_start, full_end)
        folds = {
            "FULL": (full_start, full_end),
            "TRAIN_H1": (full_start, mid),
            "TEST_H2": (mid, full_end),
        }
        results[asset] = {}
        for fold_name, (st, en) in folds.items():
            results[asset][fold_name] = {}
            for variant in overrides_to_test:
                key = variant["label"]
                summary = run_one(preset, variant["overrides"], st, en)
                results[asset][fold_name][key] = summary
                pdd = (summary["net_pnl"] / summary["max_dd_$"]) if summary["max_dd_$"] else 0
                print(f"  {asset:<7s} | {fold_name:<10s} | {key:<32s} | "
                      f"PnL=${summary['net_pnl']:>9,.0f} | "
                      f"DD=${summary['max_dd_$']:>6,.0f} | "
                      f"P/DD={pdd:>5.1f} | "
                      f"N={summary['trades']:>4d}")
            print()
        # Compute deltas H6 vs OFF per fold
        for fold_name in ["FULL", "TRAIN_H1", "TEST_H2"]:
            off = results[asset][fold_name]["OFF (V3 baseline)"]
            for v in overrides_to_test[1:]:
                on = results[asset][fold_name][v["label"]]
                dpnl = on["net_pnl"] - off["net_pnl"]
                ddd = on["max_dd_$"] - off["max_dd_$"]
                print(f"    {asset} {fold_name} delta ({v['label']}): "
                      f"ΔPnL={dpnl:+,.0f} ΔDD={ddd:+,.0f}")
        print()
    out = Path(__file__).resolve().parent / "logs" / "phase4_walkforward.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(results, indent=2))
    print(f"\nResults → {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
