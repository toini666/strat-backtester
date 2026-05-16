"""07d — Final levers: partial-exit at HW cross, max_contracts cap, fine risk grid.

If none push P/DD past 12, declare best-effort.
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

    print("=== 07d-A hw_partial_pct sweep at r=0.005 ===\n", flush=True)
    for pct in (0, 15, 25, 35, 50):
        for rr_min in (0.0, 0.5, 1.0):
            params = dict(WINNER_PARAMS)
            params["hw_partial_pct"] = float(pct)
            params["hw_partial_min_rr"] = float(rr_min)
            s = bench(
                label=f"hw_part={pct}% rr_min={rr_min}",
                strategy_name=C.STRATEGY, symbol=C.SYMBOL,
                interval=TF, start=C.START, end=C.END,
                strategy_params=params,
                initial_equity=C.INITIAL_EQUITY,
                risk_per_trade=0.005,
                max_contracts=C.MAX_CONTRACTS,
                engine_settings=es,
            )
            s["hw_partial_pct"] = pct
            s["hw_partial_min_rr"] = rr_min
            s["ratio_p_dd"] = round(s["net_pnl"] / s["max_dd_$"], 2) if s["max_dd_$"] > 0 else None
            s["meets_both"] = s["net_pnl"] > C.TARGET_PNL and s["max_dd_$"] < C.TARGET_MAX_DD
            rows.append(s)

    print("\n=== 07d-B max_contracts cap at r=0.005 and r=0.01 ===\n", flush=True)
    for mc in (3, 5, 7, 10, 15, 20, 30, 50):
        for risk in (0.005, 0.008, 0.01):
            s = bench(
                label=f"max_contracts={mc} r={risk:.4f}",
                strategy_name=C.STRATEGY, symbol=C.SYMBOL,
                interval=TF, start=C.START, end=C.END,
                strategy_params=WINNER_PARAMS,
                initial_equity=C.INITIAL_EQUITY,
                risk_per_trade=risk,
                max_contracts=mc,
                engine_settings=es,
            )
            s["max_contracts"] = mc
            s["risk"] = risk
            s["ratio_p_dd"] = round(s["net_pnl"] / s["max_dd_$"], 2) if s["max_dd_$"] > 0 else None
            s["meets_both"] = s["net_pnl"] > C.TARGET_PNL and s["max_dd_$"] < C.TARGET_MAX_DD
            rows.append(s)

    print("\n=== 07d-C fine risk grid 0.0040-0.0060 (no extra lever) ===\n", flush=True)
    for risk in (0.0040, 0.0042, 0.0045, 0.0048, 0.0050, 0.0052, 0.0055, 0.0058, 0.0060):
        s = bench(
            label=f"r={risk:.4f}",
            strategy_name=C.STRATEGY, symbol=C.SYMBOL,
            interval=TF, start=C.START, end=C.END,
            strategy_params=WINNER_PARAMS,
            initial_equity=C.INITIAL_EQUITY,
            risk_per_trade=risk,
            max_contracts=C.MAX_CONTRACTS,
            engine_settings=es,
        )
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
        print("  (none — top 15 by P/DD)")
        rows.sort(key=lambda r: r["ratio_p_dd"] or 0, reverse=True)
        for r in rows[:15]:
            print(f"  P/DD={r['ratio_p_dd']}  PnL=${r['net_pnl']:>9,.0f}  DD=${r['max_dd_$']:>5,.0f}  -- {r['label']}")

    out = Path(__file__).resolve().parents[1] / "logs" / "07d_partial_and_caps.json"
    out.write_text(json.dumps(rows, indent=2, default=str))
    print(f"\n[saved] {out}")


if __name__ == "__main__":
    main()
