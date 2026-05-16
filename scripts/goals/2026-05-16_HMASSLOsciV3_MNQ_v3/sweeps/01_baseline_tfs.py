"""01 — Baseline: replay v2 winner params with NO time-of-day blackouts.

We run two reference points per TF:

  A) `defaults`  — strategy default_params, UI defaults engine settings
                   (only 22-23:59 blackout active for HMASSLOsciV3).
  B) `v2_winner` — params copied from the v2 winner preset, same UI defaults
                   engine (no extra blackouts). This isolates "what we lose
                   by removing the 6 hourly blackouts the v2 winner relied on".

Per goal file, 7m is priority and 10m is alternative. We also include 3m/5m
for context (v2 report showed M3 NEGATIVE on full history, so it's expected
to confirm the same).
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _campaign as C  # noqa: E402

from scripts.goals._shared.harness import bench  # noqa: E402


def main():
    print(f"=== 01 BASELINE TFs — {C.STRATEGY} on {C.SYMBOL} ===")
    print(f"Period: {C.START} → {C.END}   risk={C.DEFAULT_RISK}")
    print("Engine: UI defaults (only blackout 22:00-23:59 active)\n")

    rows = []
    for tf in C.ALL_TFS:
        rows.append(("defaults", tf, bench(
            f"defaults    TF={tf:<4s}",
            strategy_name=C.STRATEGY,
            symbol=C.SYMBOL,
            interval=tf,
            start=C.START,
            end=C.END,
            strategy_params=None,
            initial_equity=C.INITIAL_EQUITY,
            risk_per_trade=C.DEFAULT_RISK,
            max_contracts=C.MAX_CONTRACTS,
        )))

    print()
    for tf in C.ALL_TFS:
        rows.append(("v2_winner", tf, bench(
            f"v2_winner   TF={tf:<4s}",
            strategy_name=C.STRATEGY,
            symbol=C.SYMBOL,
            interval=tf,
            start=C.START,
            end=C.END,
            strategy_params=C.PREV_WINNER_PARAMS,
            initial_equity=C.INITIAL_EQUITY,
            risk_per_trade=C.DEFAULT_RISK,
            max_contracts=C.MAX_CONTRACTS,
        )))

    print("\n--- Ranked by Profit/DD ratio ---")
    ranked = sorted(rows, key=lambda x: x[2]["net_pnl"] / max(x[2]["max_dd_$"], 1.0),
                    reverse=True)
    for label, tf, s in ranked:
        ratio = s["net_pnl"] / max(s["max_dd_$"], 1.0)
        print(f"  {label:<10s} TF={tf:<4s}  ratio={ratio:>6.2f}  "
              f"PnL=${s['net_pnl']:>9,.0f}  DD=${s['max_dd_$']:>6,.0f}  "
              f"PF={s['profit_factor']}  N={s['trades']}")


if __name__ == "__main__":
    main()
