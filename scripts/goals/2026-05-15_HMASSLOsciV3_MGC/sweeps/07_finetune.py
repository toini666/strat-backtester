"""07 — Finetune combo around the best (TF, params, risk, blackouts) found so far.

Search a small grid (±1 step) around the leading config to find the corner
that satisfies both objectives (PnL > $30k, DD < $2.5k).
"""

from __future__ import annotations

import itertools
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
WINNER_RISK = 0.005
WINNER_BLACKOUTS = [
    (11, 0, 12, 0),
    (8, 0, 9, 0),
    (3, 0, 4, 0),
]


# Try ADDITIVE param boosts on top of the winner. Each row tested independently
# (single delta vs WINNER_PARAMS) at risk=0.005 to see whether it lifts P/DD past 12.
DELTAS = [
    ("base (winner)", {}),
    ("+hma_pol_bars=4", {"hma_pol_bars": 4}),
    ("+hma_pol_bars=5", {"hma_pol_bars": 5}),
    ("+hma_pol_bars=6", {"hma_pol_bars": 6}),
    ("+hma_pol_bars=0", {"hma_pol_bars": 0}),
    ("+sig_extreme=25", {"sig_extreme": 25.0}),
    ("+sig_extreme=20", {"sig_extreme": 20.0}),
    ("+sig_extreme=15", {"sig_extreme": 15.0}),
    ("+max_sl_points=50", {"max_sl_points": 50.0}),
    ("+max_sl_points=100", {"max_sl_points": 100.0}),
    ("+hma1_len=17", {"hma1_len": 17}),
    ("+entry_window_bars=4", {"entry_window_bars": 4}),
    ("+entry_window_bars=3", {"entry_window_bars": 3}),
    ("+entry_window_bars=2", {"entry_window_bars": 2}),
    ("+hyper_wave_length=7", {"hyper_wave_length": 7}),
    ("+hyper_wave_length=9", {"hyper_wave_length": 9}),
    ("+cloud_on=True", {"cloud_on": True}),
    ("+hma_pol_bars=5 +sig_25",
        {"hma_pol_bars": 5, "sig_extreme": 25.0}),
    ("+hma_pol_bars=5 +sig_25 +max_sl_50",
        {"hma_pol_bars": 5, "sig_extreme": 25.0, "max_sl_points": 50.0}),
    ("+hma_pol_bars=5 +sig_25 +ew_4",
        {"hma_pol_bars": 5, "sig_extreme": 25.0, "entry_window_bars": 4}),
    ("+hma_pol_bars=6 +sig_25",
        {"hma_pol_bars": 6, "sig_extreme": 25.0}),
    ("+hma_pol_bars=4 +sig_20 +max_sl_50",
        {"hma_pol_bars": 4, "sig_extreme": 20.0, "max_sl_points": 50.0}),
]


def main():
    print(f"=== 07 FINETUNE additive deltas — base {WINNER_PARAMS} risk={WINNER_RISK} ===\n", flush=True)
    es = make_engine_settings(
        C.STRATEGY,
        extra_active_windows=[{"start_hour": sh, "start_minute": sm,
                               "end_hour": eh, "end_minute": em}
                              for (sh, sm, eh, em) in WINNER_BLACKOUTS],
    )

    rows = []
    for label, delta in DELTAS:
        overrides = dict(WINNER_PARAMS)
        overrides.update(delta)
        s = bench(
            label=label,
            strategy_name=C.STRATEGY, symbol=C.SYMBOL,
            interval=TF, start=C.START, end=C.END,
            strategy_params=overrides,
            initial_equity=C.INITIAL_EQUITY,
            risk_per_trade=WINNER_RISK,
            max_contracts=C.MAX_CONTRACTS,
            engine_settings=es,
        )
        s["overrides"] = overrides
        s["ratio_p_dd"] = round(s["net_pnl"] / s["max_dd_$"], 2) if s["max_dd_$"] > 0 else None
        s["meets_pnl"] = s["net_pnl"] > C.TARGET_PNL
        s["meets_dd"] = s["max_dd_$"] < C.TARGET_MAX_DD
        s["meets_both"] = s["meets_pnl"] and s["meets_dd"]
        rows.append(s)

    print()
    print("=== Ranking by Profit/DD ratio ===")
    rows.sort(key=lambda r: (r["ratio_p_dd"] or -999), reverse=True)
    for r in rows:
        flag = "✓✓" if r["meets_both"] else ("·P" if r["meets_pnl"] else "  ") + ("·DD" if r["meets_dd"] else "   ")
        print(f"  {flag} P/DD={r['ratio_p_dd']:>5}  PnL=${r['net_pnl']:>9,.0f}  "
              f"DD=${r['max_dd_$']:>5,.0f}  N={r['trades']:>4}  -- {r['label']}")

    out = Path(__file__).resolve().parents[1] / "logs" / "07_finetune.json"
    out.write_text(json.dumps(rows, indent=2, default=str))
    print(f"\n[saved] {out}")


if __name__ == "__main__":
    main()
