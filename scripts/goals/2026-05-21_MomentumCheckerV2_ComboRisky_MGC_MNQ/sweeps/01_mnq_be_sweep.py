"""Phase 01 — MNQ be_at_rr sweep.

Prior combo campaign found MNQ be_at_rr=2.0-2.4 was the single biggest
DD-cut lever with low PnL cost. The COMBO RIsky preset has MNQ be_at_rr=0,
so this lever is unused — exact same situation. Sweep aggressively.
"""
from __future__ import annotations

from _campaign import MNQ_PARAMS_BASE, fmt_multi, run_multi  # noqa: E402

VALUES = [0, 1.0, 1.5, 1.8, 2.0, 2.2, 2.4, 2.6, 3.0]

if __name__ == "__main__":
    print("MNQ be_at_rr sweep (MGC unchanged, risks unchanged):\n")
    rows = []
    for v in VALUES:
        p = dict(MNQ_PARAMS_BASE)
        p["be_at_rr"] = v
        s = run_multi(mnq_params=p)
        marker = "  ✓" if s["max_dd_$"] < 2500 else ""
        line = f"  be_at_rr={v:<4}  {fmt_multi(s)}{marker}"
        print(line)
        rows.append((v, s))

    print("\nBest by DD:")
    best_dd = min(rows, key=lambda r: r[1]["max_dd_$"])
    print(f"  be={best_dd[0]}  PnL=${best_dd[1]['net_pnl']:,.0f}  DD=${best_dd[1]['max_dd_$']:,.0f}")
    print("Best PnL with DD<$2,500:")
    valid = [r for r in rows if r[1]["max_dd_$"] < 2500]
    if valid:
        best = max(valid, key=lambda r: r[1]["net_pnl"])
        print(f"  be={best[0]}  PnL=${best[1]['net_pnl']:,.0f}  DD=${best[1]['max_dd_$']:,.0f}")
    else:
        print("  (none satisfy DD<$2,500 yet)")
