"""Phase 15 — final winner search.

Stack Phase 14's wins:
- MNQ=0.34% + MNQ_be=2.4 → $92,273 / $2,292 (margin $8)
- mcp=0.26 + MNQ_be=2.4 → $93,802 / $2,313 (over $13)

Try: MNQ=0.34% + mcp=0.26 + MNQ_be=2.4 — may stack to $92k+ at DD ≤ $2,292.
Also explore neighbors of MNQ_be=2.4 (2.35, 2.45) and MGC=0.49%/0.50%.
"""
import time
from _campaign import (
    MGC_PARAMS_BASE, MNQ_PARAMS_BASE,
    run_multi, fmt_multi,
)


def run_cfg(*, mgc_risk, mnq_risk, mgc_overrides=None, mnq_overrides=None):
    mgc_p = dict(MGC_PARAMS_BASE)
    mgc_p["sl_max_points"] = 80
    if mgc_overrides:
        mgc_p.update(mgc_overrides)
    mnq_p = dict(MNQ_PARAMS_BASE)
    if mnq_overrides:
        mnq_p.update(mnq_overrides)
    return run_multi(
        mgc_params=mgc_p, mgc_risk=mgc_risk,
        mnq_params=mnq_p, mnq_risk=mnq_risk,
    )


def main():
    rows = []
    tests = [
        # (label, mgc_r, mnq_r, mcp, be_mgc, mnq_be)
        # Stacked combos with MNQ=0.34% + MNQ_be=2.4
        ("MNQ=0.34% mcp=0.26 MNQ_be=2.4", 0.0050, 0.0034, 0.26, 2.0, 2.4),
        ("MNQ=0.34% mcp=0.27 MNQ_be=2.4", 0.0050, 0.0034, 0.27, 2.0, 2.4),
        ("MNQ=0.34% mcp=0.26 MNQ_be=2.4 MGC=0.49%", 0.0049, 0.0034, 0.26, 2.0, 2.4),
        ("MNQ=0.34% mcp=0.26 MNQ_be=2.4 MGC=0.48%", 0.0048, 0.0034, 0.26, 2.0, 2.4),
        ("MNQ=0.34% mcp=0.26 MNQ_be=2.4 MGC=0.51%", 0.0051, 0.0034, 0.26, 2.0, 2.4),
        ("MNQ=0.34% MNQ_be=2.4 MGC=0.49%", 0.0049, 0.0034, 0.25, 2.0, 2.4),
        # MNQ_be neighbors
        ("MNQ=0.34% mcp=0.26 MNQ_be=2.35", 0.0050, 0.0034, 0.26, 2.0, 2.35),
        ("MNQ=0.34% mcp=0.26 MNQ_be=2.45", 0.0050, 0.0034, 0.26, 2.0, 2.45),
        ("MNQ=0.34% mcp=0.26 MNQ_be=2.5", 0.0050, 0.0034, 0.26, 2.0, 2.5),
        ("MNQ=0.34% mcp=0.26 MNQ_be=2.3", 0.0050, 0.0034, 0.26, 2.0, 2.3),
        # MNQ risk slight bumps
        ("MNQ=0.345% mcp=0.26 MNQ_be=2.4", 0.0050, 0.00345, 0.26, 2.0, 2.4),
        ("MNQ=0.355% mcp=0.26 MNQ_be=2.4", 0.0050, 0.00355, 0.26, 2.0, 2.4),
        # MGC risk variations
        ("MNQ=0.34% mcp=0.26 MNQ_be=2.4 MGC=0.52%", 0.0052, 0.0034, 0.26, 2.0, 2.4),
        ("MNQ=0.34% mcp=0.26 MNQ_be=2.4 MGC=0.53%", 0.0053, 0.0034, 0.26, 2.0, 2.4),
    ]

    for label, mgc_r, mnq_r, mcp, be_mgc, mnq_be in tests:
        t0 = time.time()
        s = run_cfg(
            mgc_risk=mgc_r, mnq_risk=mnq_r,
            mgc_overrides={"max_candle_pct": mcp, "be_at_rr": be_mgc},
            mnq_overrides={"be_at_rr": mnq_be},
        )
        dt = time.time() - t0
        print(f"{label:<50s} {fmt_multi(s)}  ({dt:.1f}s)")
        rows.append((label, s, mgc_r, mnq_r, mcp, be_mgc, mnq_be))

    print()
    print("=" * 110)
    print("TOP under $2,300 — sorted by PnL")
    print("=" * 110)
    under = [r for r in rows if r[1]["max_dd_$"] <= 2300]
    for label, s, *_ in sorted(under, key=lambda r: -r[1]["net_pnl"])[:10]:
        margin = 2300 - s["max_dd_$"]
        print(f"  ✅ {label:<50s} PnL=${s['net_pnl']:>9,.0f} DD=${s['max_dd_$']:>6,.0f}  margin=${margin:>5,.0f}")

    print()
    print("=" * 110)
    print("Near $2,300-$2,400")
    print("=" * 110)
    near = [r for r in rows if 2300 < r[1]["max_dd_$"] <= 2400]
    for label, s, *_ in sorted(near, key=lambda r: -r[1]["net_pnl"])[:10]:
        gap = s["max_dd_$"] - 2300
        print(f"  ⚠️  {label:<50s} PnL=${s['net_pnl']:>9,.0f} DD=${s['max_dd_$']:>6,.0f}  over ${gap:>4,.0f}")


if __name__ == "__main__":
    main()
