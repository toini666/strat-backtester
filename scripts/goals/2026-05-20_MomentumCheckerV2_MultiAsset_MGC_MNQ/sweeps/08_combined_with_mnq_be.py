"""Phase 8 — joint risk + MNQ be_at_rr around the breakthrough config.

Anchor: MGC sl_max=80, MNQ be_at_rr=1.5 → $78,055 / $2,270.
Explore:
  - MGC risk × MNQ risk
  - MNQ be_at_rr 1.0-2.5
  - Combine MGC rr_tp=4 (tighter $2,392 alone)
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
    print("Grid: MGC risk × MNQ risk @ MNQ be_at_rr=1.5, MGC sl_max=80")
    print("=" * 110)
    for mgc_r in [0.0040, 0.0045, 0.0050, 0.0055]:
        for mnq_r in [0.0020, 0.0025, 0.0030, 0.0035, 0.0040, 0.0050]:
            t0 = time.time()
            s = run_cfg(
                mgc_risk=mgc_r, mnq_risk=mnq_r,
                mnq_overrides={"be_at_rr": 1.5},
            )
            dt = time.time() - t0
            label = f"MGC={mgc_r*100:.2f}% MNQ={mnq_r*100:.2f}%"
            print(f"{label:<28s} {fmt_multi(s)}  ({dt:.1f}s)")
            rows.append((label, mgc_r, mnq_r, s, "be=1.5"))

    print()
    print("=" * 110)
    print("Same grid @ MNQ be_at_rr=2.0")
    print("=" * 110)
    for mgc_r in [0.0040, 0.0045, 0.0050, 0.0055]:
        for mnq_r in [0.0020, 0.0025, 0.0030, 0.0035, 0.0040, 0.0050]:
            t0 = time.time()
            s = run_cfg(
                mgc_risk=mgc_r, mnq_risk=mnq_r,
                mnq_overrides={"be_at_rr": 2.0},
            )
            dt = time.time() - t0
            label = f"MGC={mgc_r*100:.2f}% MNQ={mnq_r*100:.2f}%"
            print(f"{label:<28s} {fmt_multi(s)}  ({dt:.1f}s)")
            rows.append((label, mgc_r, mnq_r, s, "be=2.0"))

    print()
    print("=" * 110)
    print("All configs ≤ $2,300 sorted by PnL (target ≤ $2,000 🎯)")
    print("=" * 110)
    under = [r for r in rows if r[3]["max_dd_$"] <= 2300]
    for label, mgc_r, mnq_r, s, be in sorted(under, key=lambda r: -r[3]["net_pnl"]):
        flag = "🎯" if s["max_dd_$"] <= 2000 else "✅"
        print(f"  {flag} {label:<28s} {be:<8s} PnL=${s['net_pnl']:>9,.0f} DD=${s['max_dd_$']:>6,.0f} "
              f"P/DD={s['net_pnl']/max(s['max_dd_$'],1):>5.1f}")


if __name__ == "__main__":
    main()
