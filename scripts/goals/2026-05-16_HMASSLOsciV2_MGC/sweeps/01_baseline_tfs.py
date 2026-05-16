"""Sweep 01 — Baseline timeframes for HMASSLOsciV2 on MGC."""

from __future__ import annotations

import json
from pathlib import Path

from _campaign import (
    ALL_TFS,
    DEFAULT_RISK,
    END,
    INITIAL_EQUITY,
    MAX_CONTRACTS,
    START,
    STRATEGY,
    SYMBOL,
)

from scripts.goals._shared.harness import bench


def main():
    print(f"=== Sweep 01: baseline TFs — {STRATEGY} / {SYMBOL} ({START} → {END}) ===")
    print(f"    risk={DEFAULT_RISK} | equity=${INITIAL_EQUITY:,.0f} | max_contracts={MAX_CONTRACTS}")
    print()
    rows = []
    for tf in ALL_TFS:
        s = bench(
            label=f"baseline-{tf}",
            strategy_name=STRATEGY,
            symbol=SYMBOL,
            interval=tf,
            start=START,
            end=END,
            initial_equity=INITIAL_EQUITY,
            risk_per_trade=DEFAULT_RISK,
            max_contracts=MAX_CONTRACTS,
        )
        s["tf"] = tf
        s["ratio_p_dd"] = round(s["net_pnl"] / s["max_dd_$"], 2) if s["max_dd_$"] > 0 else None
        rows.append(s)

    print()
    print("=== Ranking by Profit/DD ratio ===")
    rows.sort(key=lambda r: (r["ratio_p_dd"] or -999), reverse=True)
    for r in rows:
        print(f"  {r['tf']:<5s} PnL=${r['net_pnl']:>9,.0f}  DD=${r['max_dd_$']:>6,.0f}  "
              f"PF={r['profit_factor']}  N={r['trades']:>4}  WR={r['win_rate']}%  "
              f"P/DD={r['ratio_p_dd']}")

    out = Path(__file__).resolve().parents[1] / "logs" / "01_baseline_tfs.json"
    out.write_text(json.dumps(rows, indent=2, default=str))
    print(f"\n[saved] {out}")


if __name__ == "__main__":
    main()
