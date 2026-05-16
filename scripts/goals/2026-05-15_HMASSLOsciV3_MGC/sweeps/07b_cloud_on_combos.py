"""07b — Cloud_on combo deepdive.

cloud_on=True was the only delta in 07_finetune that tightened DD enough to be
near the target. Try combining it with different blackout sets and risk levels.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _campaign as C  # noqa: E402

from scripts.goals._shared.engine_settings import make_engine_settings  # noqa: E402
from scripts.goals._shared.harness import bench  # noqa: E402

TF = "7m"

BASE_PARAMS = {
    "hw_range_on": True,
    "hma2_len": 34,
    "cloud_on": True,
}

BLACKOUT_SETS = [
    ("none",                   []),
    ("11h",                    [(11, 0, 12, 0)]),
    ("11h+03h",                [(11, 0, 12, 0), (3, 0, 4, 0)]),
    ("11h+03h+08h",            [(11, 0, 12, 0), (3, 0, 4, 0), (8, 0, 9, 0)]),
    ("11h+03h+17h",            [(11, 0, 12, 0), (3, 0, 4, 0), (17, 0, 18, 0)]),
    ("11h+03h+23h",            [(11, 0, 12, 0), (3, 0, 4, 0), (23, 0, 0, 0)]),
    ("11h+03h+08h+17h",        [(11, 0, 12, 0), (3, 0, 4, 0), (8, 0, 9, 0), (17, 0, 18, 0)]),
]

RISK_LEVELS = [0.003, 0.004, 0.005, 0.006, 0.008]


def main():
    print(f"=== 07b cloud_on + blackouts + risk grid — {BASE_PARAMS} ===\n", flush=True)
    rows = []
    for label, blackouts in BLACKOUT_SETS:
        es = make_engine_settings(
            C.STRATEGY,
            extra_active_windows=[{"start_hour": sh, "start_minute": sm,
                                   "end_hour": eh, "end_minute": em}
                                  for (sh, sm, eh, em) in blackouts],
        )
        for risk in RISK_LEVELS:
            s = bench(
                label=f"BO={label} r={risk:.4f}",
                strategy_name=C.STRATEGY, symbol=C.SYMBOL,
                interval=TF, start=C.START, end=C.END,
                strategy_params=BASE_PARAMS,
                initial_equity=C.INITIAL_EQUITY,
                risk_per_trade=risk,
                max_contracts=C.MAX_CONTRACTS,
                engine_settings=es,
            )
            s["blackouts"] = blackouts
            s["risk"] = risk
            s["ratio_p_dd"] = round(s["net_pnl"] / s["max_dd_$"], 2) if s["max_dd_$"] > 0 else None
            s["meets_both"] = s["net_pnl"] > C.TARGET_PNL and s["max_dd_$"] < C.TARGET_MAX_DD
            rows.append(s)

    print()
    print("=== Configs meeting BOTH objectives (PnL > 30k, DD < 2.5k) ===")
    winners = [r for r in rows if r["meets_both"]]
    winners.sort(key=lambda r: r["ratio_p_dd"] or 0, reverse=True)
    if not winners:
        print("  (none — top 10 by P/DD anyway)")
        rows.sort(key=lambda r: r["ratio_p_dd"] or 0, reverse=True)
        for r in rows[:10]:
            print(f"  P/DD={r['ratio_p_dd']}  PnL=${r['net_pnl']:>9,.0f}  DD=${r['max_dd_$']:>5,.0f}  -- {r['label']}")
    else:
        for r in winners:
            print(f"  ✓✓ P/DD={r['ratio_p_dd']}  PnL=${r['net_pnl']:>9,.0f}  DD=${r['max_dd_$']:>5,.0f}  -- {r['label']}")

    out = Path(__file__).resolve().parents[1] / "logs" / "07b_cloud_on_combos.json"
    out.write_text(json.dumps(rows, indent=2, default=str))
    print(f"\n[saved] {out}")


if __name__ == "__main__":
    main()
