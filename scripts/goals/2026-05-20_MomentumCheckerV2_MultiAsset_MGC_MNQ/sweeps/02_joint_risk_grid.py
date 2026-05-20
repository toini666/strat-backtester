"""Phase 2 — joint risk grid (MGC × MNQ).

Phase 1 showed MNQ risk dominates DD. Push MNQ into the low-risk corner
(0.10%-0.30%) while also exploring how MGC interacts. Find the Pareto
frontier and identify configs at DD ≤ $2,300 / ≤ $2,000.
"""
import time
from _campaign import (
    MGC_PARAMS_BASE, MNQ_PARAMS_BASE,
    run_multi, fmt_multi,
)


def main():
    rows = []
    mgc_risks = [0.0030, 0.0040, 0.0050, 0.0055]
    mnq_risks = [0.0010, 0.0015, 0.0020, 0.0022, 0.0025, 0.0028, 0.0030]

    print("=" * 110)
    print(f"Joint grid: {len(mgc_risks)}×{len(mnq_risks)} = {len(mgc_risks)*len(mnq_risks)} sims")
    print("=" * 110)

    for mgc_r in mgc_risks:
        for mnq_r in mnq_risks:
            t0 = time.time()
            s = run_multi(
                mgc_params=MGC_PARAMS_BASE, mgc_risk=mgc_r,
                mnq_params=MNQ_PARAMS_BASE, mnq_risk=mnq_r,
            )
            dt = time.time() - t0
            label = f"MGC={mgc_r*100:.2f}% MNQ={mnq_r*100:.2f}%"
            print(f"{label:<30s} {fmt_multi(s)}  ({dt:.1f}s)")
            rows.append((label, mgc_r, mnq_r, s))

    print()
    print("=" * 110)
    print("DD ≤ $2,300 (HARD ceiling) — sorted by PnL desc")
    print("=" * 110)
    under_hard = [r for r in rows if r[3]["max_dd_$"] <= 2300]
    for label, mgc_r, mnq_r, s in sorted(under_hard, key=lambda r: -r[3]["net_pnl"]):
        flag = "🎯" if s["max_dd_$"] <= 2000 else "✅"
        print(f"  {flag} {label:<28s} PnL=${s['net_pnl']:>9,.0f} DD=${s['max_dd_$']:>6,.0f} "
              f"P/DD={s['net_pnl']/max(s['max_dd_$'],1):>5.1f}")

    print()
    print("=" * 110)
    print("DD ≤ $2,500 — close to goal but over hard ceiling")
    print("=" * 110)
    near_miss = [r for r in rows if 2300 < r[3]["max_dd_$"] <= 2500]
    for label, mgc_r, mnq_r, s in sorted(near_miss, key=lambda r: -r[3]["net_pnl"]):
        print(f"  ⚠️  {label:<28s} PnL=${s['net_pnl']:>9,.0f} DD=${s['max_dd_$']:>6,.0f} "
              f"P/DD={s['net_pnl']/max(s['max_dd_$'],1):>5.1f}")


if __name__ == "__main__":
    main()
