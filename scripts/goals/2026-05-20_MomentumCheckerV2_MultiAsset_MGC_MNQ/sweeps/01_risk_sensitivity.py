"""Phase 1 — per-leg risk sensitivity. Sweep one leg's risk while pinning
the other at its baseline. Identify the DD-vs-PnL curve for each leg in the
combined account.
"""
import time
from _campaign import (
    MGC_PARAMS_BASE, MNQ_PARAMS_BASE,
    run_multi, fmt_multi,
)


def main():
    rows = []
    print("=" * 110)
    print("MGC risk sweep — MNQ pinned at 0.66%")
    print("=" * 110)
    for mgc_r in [0.0025, 0.0030, 0.0035, 0.0040, 0.0045, 0.0050, 0.0055]:
        t0 = time.time()
        s = run_multi(
            mgc_params=MGC_PARAMS_BASE, mgc_risk=mgc_r,
            mnq_params=MNQ_PARAMS_BASE, mnq_risk=0.0066,
        )
        dt = time.time() - t0
        label = f"MGC={mgc_r*100:.2f}% MNQ=0.66%"
        print(f"{label:<55s} {fmt_multi(s)}  ({dt:.1f}s)")
        rows.append((label, s))

    print()
    print("=" * 110)
    print("MNQ risk sweep — MGC pinned at 0.55%")
    print("=" * 110)
    for mnq_r in [0.0030, 0.0035, 0.0040, 0.0045, 0.0050, 0.0055, 0.0060, 0.0066]:
        t0 = time.time()
        s = run_multi(
            mgc_params=MGC_PARAMS_BASE, mgc_risk=0.0055,
            mnq_params=MNQ_PARAMS_BASE, mnq_risk=mnq_r,
        )
        dt = time.time() - t0
        label = f"MGC=0.55% MNQ={mnq_r*100:.2f}%"
        print(f"{label:<55s} {fmt_multi(s)}  ({dt:.1f}s)")
        rows.append((label, s))

    print()
    print("=" * 110)
    print("SUMMARY (sorted by DD, DD ≤ $2,300 marked ✅)")
    print("=" * 110)
    for label, s in sorted(rows, key=lambda r: r[1]["max_dd_$"]):
        flag = "✅" if s["max_dd_$"] <= 2300 else ("⚠️" if s["max_dd_$"] <= 2500 else "❌")
        print(f"  {flag} {label:<28s} PnL=${s['net_pnl']:>9,.0f} DD=${s['max_dd_$']:>6,.0f} "
              f"P/DD={s['net_pnl']/max(s['max_dd_$'],1):>5.1f}")


if __name__ == "__main__":
    main()
