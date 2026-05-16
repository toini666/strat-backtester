"""07c — Alternative exit modes + hma2_len granular sweep.

Try the "% du prix d'entrée en profit" final exit and a finer hma2_len sweep
to push P/DD past 12 (needed to fit both objectives simultaneously).
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

WINNER_PARAMS = {
    "hw_range_on": True,
    "hma2_len": 34,
}

BLACKOUTS = [(11, 0, 12, 0), (8, 0, 9, 0), (3, 0, 4, 0)]


def main():
    es = make_engine_settings(
        C.STRATEGY,
        extra_active_windows=[{"start_hour": sh, "start_minute": sm,
                               "end_hour": eh, "end_minute": em}
                              for (sh, sm, eh, em) in BLACKOUTS],
    )

    rows = []

    print("=== 07c hma2_len granular at r=0.005 ===\n", flush=True)
    for hma2 in (28, 30, 32, 34, 36, 38, 40, 45, 50, 55, 60):
        params = dict(WINNER_PARAMS)
        params["hma2_len"] = hma2
        for risk in (0.004, 0.005, 0.006):
            s = bench(
                label=f"hma2={hma2} r={risk:.4f}",
                strategy_name=C.STRATEGY, symbol=C.SYMBOL,
                interval=TF, start=C.START, end=C.END,
                strategy_params=params,
                initial_equity=C.INITIAL_EQUITY,
                risk_per_trade=risk,
                max_contracts=C.MAX_CONTRACTS,
                engine_settings=es,
            )
            s["hma2_len"] = hma2
            s["risk"] = risk
            s["ratio_p_dd"] = round(s["net_pnl"] / s["max_dd_$"], 2) if s["max_dd_$"] > 0 else None
            s["meets_both"] = s["net_pnl"] > C.TARGET_PNL and s["max_dd_$"] < C.TARGET_MAX_DD
            rows.append(s)

    print("\n=== 07c alt exit-mode % at r=0.005 (hma2=34) ===\n", flush=True)
    for pct in (0.05, 0.075, 0.1, 0.125, 0.15, 0.2, 0.25, 0.3):
        for risk in (0.004, 0.005, 0.006):
            params = dict(WINNER_PARAMS)
            params["final_exit_mode"] = "% du prix d'entrée en profit"
            params["final_exit_pct"] = pct
            s = bench(
                label=f"alt-pct={pct} r={risk:.4f}",
                strategy_name=C.STRATEGY, symbol=C.SYMBOL,
                interval=TF, start=C.START, end=C.END,
                strategy_params=params,
                initial_equity=C.INITIAL_EQUITY,
                risk_per_trade=risk,
                max_contracts=C.MAX_CONTRACTS,
                engine_settings=es,
            )
            s["final_exit_pct"] = pct
            s["risk"] = risk
            s["ratio_p_dd"] = round(s["net_pnl"] / s["max_dd_$"], 2) if s["max_dd_$"] > 0 else None
            s["meets_both"] = s["net_pnl"] > C.TARGET_PNL and s["max_dd_$"] < C.TARGET_MAX_DD
            rows.append(s)

    print()
    print("=== Configs meeting BOTH objectives ===")
    winners = [r for r in rows if r["meets_both"]]
    if winners:
        winners.sort(key=lambda r: r["ratio_p_dd"] or 0, reverse=True)
        for r in winners:
            print(f"  ✓✓ P/DD={r['ratio_p_dd']}  PnL=${r['net_pnl']:>9,.0f}  DD=${r['max_dd_$']:>5,.0f}  -- {r['label']}")
    else:
        print("  (none — top 12 by P/DD anyway)")
        rows.sort(key=lambda r: r["ratio_p_dd"] or 0, reverse=True)
        for r in rows[:12]:
            print(f"  P/DD={r['ratio_p_dd']}  PnL=${r['net_pnl']:>9,.0f}  DD=${r['max_dd_$']:>5,.0f}  -- {r['label']}")

    out = Path(__file__).resolve().parents[1] / "logs" / "07c_alt_exits_and_hma2.json"
    out.write_text(json.dumps(rows, indent=2, default=str))
    print(f"\n[saved] {out}")


if __name__ == "__main__":
    main()
