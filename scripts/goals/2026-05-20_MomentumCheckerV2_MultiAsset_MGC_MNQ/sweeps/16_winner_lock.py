"""Phase 16 — winner lock. The $96k breakthrough at MGC=0.53% with MNQ=0.34%
mcp=0.26 MNQ_be=2.4 suggests favorable rounding. Test MGC=0.53-0.56% neighbors.
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
    print("=" * 110)
    print("MGC risk fine grid 0.525-0.575 at MNQ=0.34% mcp=0.26 MNQ_be=2.4")
    print("=" * 110)
    for mgc_r in [0.00525, 0.00530, 0.00535, 0.00540, 0.00545, 0.00550, 0.00555, 0.00560, 0.00565, 0.00570]:
        t0 = time.time()
        s = run_cfg(
            mgc_risk=mgc_r, mnq_risk=0.0034,
            mgc_overrides={"max_candle_pct": 0.26, "be_at_rr": 2.0},
            mnq_overrides={"be_at_rr": 2.4},
        )
        dt = time.time() - t0
        label = f"MGC={mgc_r*100:.3f}%"
        print(f"{label:<50s} {fmt_multi(s)}  ({dt:.1f}s)")
        rows.append((label, s))

    print()
    print("=" * 110)
    print("Variations around MGC=0.53% winner")
    print("=" * 110)
    tests = [
        ("MGC=0.53% MNQ=0.33%", 0.0053, 0.0033, 0.26, 2.0, 2.4),
        ("MGC=0.53% MNQ=0.345%", 0.0053, 0.00345, 0.26, 2.0, 2.4),
        ("MGC=0.53% MNQ=0.35%", 0.0053, 0.0035, 0.26, 2.0, 2.4),
        ("MGC=0.53% mcp=0.25", 0.0053, 0.0034, 0.25, 2.0, 2.4),
        ("MGC=0.53% mcp=0.27", 0.0053, 0.0034, 0.27, 2.0, 2.4),
        ("MGC=0.53% MNQ_be=2.5", 0.0053, 0.0034, 0.26, 2.0, 2.5),
        ("MGC=0.53% MNQ_be=2.3", 0.0053, 0.0034, 0.26, 2.0, 2.3),
        ("MGC=0.53% be_mgc=1.8", 0.0053, 0.0034, 0.26, 1.8, 2.4),
        ("MGC=0.53% be_mgc=1.9", 0.0053, 0.0034, 0.26, 1.9, 2.4),
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
        rows.append((label, s))

    print()
    print("=" * 110)
    print("FINAL TOP under $2,300 — WINNER CANDIDATES")
    print("=" * 110)
    under = [r for r in rows if r[1]["max_dd_$"] <= 2300]
    for label, s in sorted(under, key=lambda r: -r[1]["net_pnl"])[:15]:
        margin = 2300 - s["max_dd_$"]
        print(f"  ✅ {label:<50s} PnL=${s['net_pnl']:>9,.0f} DD=${s['max_dd_$']:>6,.0f}  margin=${margin:>5,.0f}")


if __name__ == "__main__":
    main()
