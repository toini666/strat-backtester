"""04 — Risk per trade sweep (daily limits stay DISABLED per user instruction).

Base = M7 + best params from sweep 03 (filled in after the 1D sweep finishes).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _campaign as C  # noqa: E402

from scripts.goals._shared.harness import bench  # noqa: E402

TF = "7m"

# Updated after 03_strategy_params.json analysis. BASE_PARAMS combines the best
# value of each 1-D sweep (kept conservative — only changes with material P/DD lift).
BASE_PARAMS = {
    "hw_range_on": True,
    "hma2_len": 34,
}

# Best 3-blackout combo from sweep 06 (PnL=$64k, DD=$6.5k at risk=0.01).
BLACKOUTS = [
    (11, 0, 12, 0),
    (8, 0, 9, 0),
    (3, 0, 4, 0),
]


def main():
    print(f"=== 04 RISK sweep — base M7 {BASE_PARAMS} + 3 blackouts (no daily limits) ===\n", flush=True)
    from scripts.goals._shared.engine_settings import make_engine_settings  # noqa: E402
    es = make_engine_settings(
        C.STRATEGY,
        extra_active_windows=[{"start_hour": sh, "start_minute": sm,
                               "end_hour": eh, "end_minute": em}
                              for (sh, sm, eh, em) in BLACKOUTS],
    )
    rows = []
    for risk in (0.001, 0.0015, 0.002, 0.0025, 0.003, 0.004, 0.005, 0.0075, 0.01):
        s = bench(
            label=f"r={risk:.4f}",
            strategy_name=C.STRATEGY, symbol=C.SYMBOL,
            interval=TF, start=C.START, end=C.END,
            strategy_params=BASE_PARAMS,
            initial_equity=C.INITIAL_EQUITY,
            risk_per_trade=risk,
            max_contracts=C.MAX_CONTRACTS,
            engine_settings=es,
        )
        s["risk"] = risk
        s["ratio_p_dd"] = round(s["net_pnl"] / s["max_dd_$"], 2) if s["max_dd_$"] > 0 else None
        rows.append(s)

    print()
    print("=== Ranking by Profit/DD ratio ===")
    rows.sort(key=lambda r: (r["ratio_p_dd"] or -999), reverse=True)
    for r in rows:
        print(f"  r={r['risk']:.4f}  P/DD={r['ratio_p_dd']:>5}  "
              f"PnL=${r['net_pnl']:>9,.0f}  DD=${r['max_dd_$']:>6,.0f}  "
              f"N={r['trades']:>4}")

    out = Path(__file__).resolve().parents[1] / "logs" / "04_risk_sweep.json"
    out.write_text(json.dumps(rows, indent=2, default=str))
    print(f"\n[saved] {out}")


if __name__ == "__main__":
    main()
