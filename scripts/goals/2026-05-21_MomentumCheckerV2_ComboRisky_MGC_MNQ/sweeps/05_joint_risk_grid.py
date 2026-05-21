"""Phase 05 — Joint risk grid near the DD<$2,500 boundary.

MGC dominates PnL contribution; MNQ dominates DD. Find the cell with max
PnL given DD<$2,500. Also test be_at_rr=2.4 on MNQ (free PnL from prior
campaign).
"""
from __future__ import annotations

from _campaign import MNQ_PARAMS_BASE, fmt_multi, run_multi  # noqa: E402

# Focus on the boundary: MNQ risk in [0.0036, 0.0045], MGC in [0.0050, 0.0060]
MGC_RISKS = [0.0055, 0.0053]
MNQ_RISKS = [0.0045, 0.0042, 0.0040, 0.0038, 0.0036, 0.0033]
BE_VALUES = [0, 2.4]

if __name__ == "__main__":
    print("Joint MGC×MNQ risk + MNQ be_at_rr grid:\n")
    rows = []
    for be in BE_VALUES:
        for mgc_r in MGC_RISKS:
            for mnq_r in MNQ_RISKS:
                p = dict(MNQ_PARAMS_BASE)
                p["be_at_rr"] = be
                s = run_multi(mgc_risk=mgc_r, mnq_risk=mnq_r, mnq_params=p)
                marker = " ✓" if s["max_dd_$"] < 2500 else ""
                line = (f"  be={be:>3}  MGC={mgc_r:.4f}  MNQ={mnq_r:.4f}  "
                        f"PnL=${s['net_pnl']:>8,.0f}  DD=${s['max_dd_$']:>6,.0f}{marker}")
                print(line)
                rows.append((be, mgc_r, mnq_r, s))

    valid = [r for r in rows if r[3]["max_dd_$"] < 2500]
    print("\n=== Top 8 by PnL among DD<$2,500 cells ===")
    valid.sort(key=lambda r: r[3]["net_pnl"], reverse=True)
    for be, mgc_r, mnq_r, s in valid[:8]:
        print(f"  be={be}  MGC={mgc_r:.4f}  MNQ={mnq_r:.4f}  "
              f"PnL=${s['net_pnl']:>8,.0f}  DD=${s['max_dd_$']:>6,.0f}  "
              f"MGC_pnl=${s['mgc']['pnl']:>7,.0f}  MNQ_pnl=${s['mnq']['pnl']:>7,.0f}")
