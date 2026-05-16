"""08 — Final validation on the full requested period.

Re-runs the winner + 3-5 close alternatives. Prints metrics that should be
saved into REPORT.md and used to populate winner_preset.json + verify_preset.py.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _campaign as C  # noqa: E402

from scripts.goals._shared.engine_settings import make_engine_settings  # noqa: E402
from scripts.goals._shared.harness import bench, run_backtest, summarize  # noqa: E402

TF = "7m"

# Populated from sweep 07's top-K winners.
_BO = [(11, 0, 12, 0), (8, 0, 9, 0), (3, 0, 4, 0)]
CANDIDATES = [
    ("WINNER cloud_on r=0.005",
        {"hw_range_on": True, "hma2_len": 34, "cloud_on": True}, 0.005, _BO),
    ("alt no-cloud r=0.005",
        {"hw_range_on": True, "hma2_len": 34}, 0.005, _BO),
    ("alt no-cloud r=0.003 (DD passes)",
        {"hw_range_on": True, "hma2_len": 34}, 0.003, _BO),
    ("alt no-cloud max_sl=100 r=0.005",
        {"hw_range_on": True, "hma2_len": 34, "max_sl_points": 100.0}, 0.005, _BO),
    ("alt cloud_on 2BO 11h+03h r=0.005",
        {"hw_range_on": True, "hma2_len": 34, "cloud_on": True}, 0.005,
        [(11, 0, 12, 0), (3, 0, 4, 0)]),
]


def main():
    print(f"=== 08 FINAL VALIDATION — {C.STRATEGY} / {C.SYMBOL} ({TF}) ===\n", flush=True)
    print(f"Period: {C.START} → {C.END}\n", flush=True)

    rows = []
    for label, params, risk, blackouts in CANDIDATES:
        es = make_engine_settings(
            C.STRATEGY,
            extra_active_windows=[{"start_hour": sh, "start_minute": sm,
                                   "end_hour": eh, "end_minute": em}
                                  for (sh, sm, eh, em) in blackouts],
        )
        s = bench(
            label=label,
            strategy_name=C.STRATEGY, symbol=C.SYMBOL,
            interval=TF, start=C.START, end=C.END,
            strategy_params=params,
            initial_equity=C.INITIAL_EQUITY,
            risk_per_trade=risk,
            max_contracts=C.MAX_CONTRACTS,
            engine_settings=es,
        )
        s["label"] = label
        s["risk"] = risk
        s["blackouts"] = blackouts
        s["overrides"] = params
        s["ratio_p_dd"] = round(s["net_pnl"] / s["max_dd_$"], 2) if s["max_dd_$"] > 0 else None
        s["meets_pnl"] = s["net_pnl"] > C.TARGET_PNL
        s["meets_dd"] = s["max_dd_$"] < C.TARGET_MAX_DD
        rows.append(s)

    print()
    print("=== Ranked ===")
    rows.sort(key=lambda r: r["ratio_p_dd"] or 0, reverse=True)
    for r in rows:
        flag = "✅" if r["meets_pnl"] and r["meets_dd"] else "❌"
        print(f"  {flag}  P/DD={r['ratio_p_dd']}  PnL=${r['net_pnl']:,.0f}  "
              f"DD=${r['max_dd_$']:,.0f}  PF={r['profit_factor']}  -- {r['label']}")

    out = Path(__file__).resolve().parents[1] / "logs" / "08_final_validation.json"
    out.write_text(json.dumps(rows, indent=2, default=str))
    print(f"\n[saved] {out}")


if __name__ == "__main__":
    main()
