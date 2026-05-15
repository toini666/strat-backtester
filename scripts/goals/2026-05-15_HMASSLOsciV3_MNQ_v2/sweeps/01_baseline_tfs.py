"""01 — Baseline TFs.

Lance HMASSLOsciV3 sur les TFs prioritaires (3m, 5m, 7m, 10m) + extras
(2m, 15m) avec les `default_params` natifs et les UI defaults d'engine
settings (auto_close=22, seul le blackout 22:00-23:59 actif).

But: identifier le TF de départ par ratio Profit/DD.
"""

from __future__ import annotations

import sys
from pathlib import Path

# `_campaign` fixes sys.path so `scripts.goals._shared` resolves.
sys.path.insert(0, str(Path(__file__).resolve().parent))
import _campaign as C  # noqa: E402

from scripts.goals._shared.harness import bench  # noqa: E402


def main():
    print(f"=== 01 BASELINE TFs — {C.STRATEGY} on {C.SYMBOL} ===")
    print(f"Period: {C.START} → {C.END}   risk={C.DEFAULT_RISK}\n")
    results = []
    for tf in C.ALL_TFS:
        s = bench(
            f"TF={tf:<4s} defaults",
            strategy_name=C.STRATEGY,
            symbol=C.SYMBOL,
            interval=tf,
            start=C.START,
            end=C.END,
            strategy_params=None,
            initial_equity=C.INITIAL_EQUITY,
            risk_per_trade=C.DEFAULT_RISK,
            max_contracts=C.MAX_CONTRACTS,
        )
        results.append((tf, s))

    print("\n--- Ranked by Profit/DD ratio ---")
    ranked = sorted(
        results,
        key=lambda x: (x[1]["net_pnl"] / max(x[1]["max_dd_$"], 1.0)),
        reverse=True,
    )
    for tf, s in ranked:
        ratio = s["net_pnl"] / max(s["max_dd_$"], 1.0)
        print(f"  TF={tf:<4s}  ratio={ratio:>6.2f}  PnL=${s['net_pnl']:>9,.0f}  DD=${s['max_dd_$']:>6,.0f}")


if __name__ == "__main__":
    main()
