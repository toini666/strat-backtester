"""Phase 03 — MNQ risk sweep at base MGC.

DD trough is driven by repeated ~$250 MNQ losses (capped contract size means
losses scale with risk_per_trade). Step MNQ risk down. Watch for rounding
cliffs.
"""
from __future__ import annotations

from _campaign import MGC_RISK_BASE, fmt_multi, run_multi  # noqa: E402

RISKS = [0.0060, 0.0058, 0.0055, 0.0052, 0.0050, 0.0048, 0.0045, 0.0042, 0.0040, 0.0036, 0.0033, 0.0030]

if __name__ == "__main__":
    print(f"MNQ risk sweep at MGC risk={MGC_RISK_BASE:.4f}:\n")
    rows = []
    for r in RISKS:
        s = run_multi(mnq_risk=r)
        marker = "  ✓" if s["max_dd_$"] < 2500 else ""
        line = f"  MNQ_risk={r:.4f}  {fmt_multi(s)}{marker}"
        print(line)
        rows.append((r, s))

    valid = [r for r in rows if r[1]["max_dd_$"] < 2500]
    print("\nDD<$2,500 cells:")
    for r, s in valid:
        print(f"  MNQ_risk={r:.4f}  PnL=${s['net_pnl']:>8,.0f}  DD=${s['max_dd_$']:>6,.0f}")
    if valid:
        best = max(valid, key=lambda x: x[1]["net_pnl"])
        print(f"\nBest PnL with DD<$2,500: MNQ_risk={best[0]:.4f}  PnL=${best[1]['net_pnl']:,.0f}  DD=${best[1]['max_dd_$']:,.0f}")
