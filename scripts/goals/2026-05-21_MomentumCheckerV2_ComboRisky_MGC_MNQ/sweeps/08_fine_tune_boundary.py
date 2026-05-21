"""Phase 08 — fine resolution around the boundary cell.

Phase 05 winner so far: be=2.4 MGC=0.0053 MNQ=0.0040 PnL=$106,385 DD=$2,494.
The 0.0050→0.0048 cliff dropped DD ~$400. Sweep finer steps between 0.0040
and 0.0050 to see if a sweet-spot cell exists with higher PnL.
"""
from __future__ import annotations

from _campaign import MNQ_PARAMS_BASE, fmt_multi, run_multi  # noqa: E402

# 0.05 % resolution
MNQ_RISKS = [0.00500, 0.00490, 0.00480, 0.00470, 0.00460, 0.00450,
             0.00440, 0.00430, 0.00420, 0.00410, 0.00405, 0.00400,
             0.00395, 0.00390]
MGC_RISK = 0.0053

if __name__ == "__main__":
    print(f"Fine MNQ risk sweep at MGC={MGC_RISK:.4f}, MNQ be_at_rr=2.4:\n")
    p = dict(MNQ_PARAMS_BASE)
    p["be_at_rr"] = 2.4
    rows = []
    for r in MNQ_RISKS:
        s = run_multi(mgc_risk=MGC_RISK, mnq_risk=r, mnq_params=p)
        marker = " ✓" if s["max_dd_$"] < 2500 else ""
        print(f"  MNQ={r:.5f}  {fmt_multi(s)}{marker}")
        rows.append((r, s))

    print("\n=== Best PnL with DD<$2,500 ===")
    valid = [r for r in rows if r[1]["max_dd_$"] < 2500]
    valid.sort(key=lambda r: r[1]["net_pnl"], reverse=True)
    for r, s in valid[:5]:
        print(f"  MNQ={r:.5f}  PnL=${s['net_pnl']:>8,.0f}  DD=${s['max_dd_$']:>6,.0f}")
