"""Phase 4 — sl_max_points sweep on MGC. The worst single trade in the DD
episode was 1 MGC contract × ~85 pts = -$852. Tighter sl_max should cap
losses but may also whipsaw winners. Test on the combined account.
"""
import time
from _campaign import (
    MGC_PARAMS_BASE, MNQ_PARAMS_BASE,
    run_multi, fmt_multi,
)


def main():
    rows = []
    # Anchor: best <$2,500 from Phase 2 = MGC=0.50%/MNQ=0.30%
    # Sweep MGC sl_max while holding everything else
    print("=" * 110)
    print("MGC sl_max_points sweep — MGC=0.50%, MNQ=0.30%")
    print("=" * 110)
    for sl_max in [30, 40, 50, 60, 70, 80, 90, 100]:
        mgc_p = dict(MGC_PARAMS_BASE)
        mgc_p["sl_max_points"] = sl_max
        t0 = time.time()
        s = run_multi(
            mgc_params=mgc_p, mgc_risk=0.0050,
            mnq_params=MNQ_PARAMS_BASE, mnq_risk=0.0030,
        )
        dt = time.time() - t0
        label = f"MGC sl_max={sl_max}"
        print(f"{label:<25s} {fmt_multi(s)}  ({dt:.1f}s)")
        rows.append((label, sl_max, s))

    print()
    print("=" * 110)
    print("Best by PnL — sorted, DD ≤ 2,300 ✅")
    print("=" * 110)
    for label, sl_max, s in sorted(rows, key=lambda r: -r[2]["net_pnl"]):
        flag = "🎯" if s["max_dd_$"] <= 2000 else ("✅" if s["max_dd_$"] <= 2300 else "❌")
        print(f"  {flag} {label:<22s} PnL=${s['net_pnl']:>9,.0f} DD=${s['max_dd_$']:>6,.0f}")


if __name__ == "__main__":
    main()
