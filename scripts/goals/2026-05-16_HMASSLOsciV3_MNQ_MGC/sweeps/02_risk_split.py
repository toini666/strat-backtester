"""02_risk_split — sweep MNQ and MGC risk independently (combined DD < $2500)."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _campaign import bench, DD_BUDGET, PNL_TARGET, MNQ_BASE_RISK, MGC_BASE_RISK  # noqa: E402


def main() -> None:
    print(f"{'='*120}")
    print("02 risk split — find best (risk_mnq, risk_mgc) under DD<$2500\n")

    # Step 1: equi-proportional downscaling to fit DD budget.
    print("--- Step 1: uniform scale-down")
    results = []
    for scale in (0.65, 0.70, 0.75, 0.80, 0.85, 0.90, 0.95, 1.00):
        s = bench(
            f"scale={scale:.2f}",
            mnq_risk=MNQ_BASE_RISK * scale, mgc_risk=MGC_BASE_RISK * scale,
        )
        results.append(("scale", scale, s))

    # Step 2: fix one leg, sweep the other.
    print("\n--- Step 2: MNQ risk sweep, MGC fixed at 0.75x")
    mgc_r = MGC_BASE_RISK * 0.75
    for sm in (0.55, 0.60, 0.65, 0.70, 0.75, 0.80, 0.85, 0.90, 1.00):
        s = bench(
            f"m={sm:.2f}/g=0.75",
            mnq_risk=MNQ_BASE_RISK * sm, mgc_risk=mgc_r,
        )
        results.append(("mnq_sweep_g075", sm, s))

    print("\n--- Step 3: MGC risk sweep, MNQ fixed at 0.85x")
    mnq_r = MNQ_BASE_RISK * 0.85
    for sg in (0.55, 0.60, 0.65, 0.70, 0.75, 0.80, 0.85, 0.90, 1.00):
        s = bench(
            f"m=0.85/g={sg:.2f}",
            mnq_risk=mnq_r, mgc_risk=MGC_BASE_RISK * sg,
        )
        results.append(("mgc_sweep_m085", sg, s))

    # Summary: sort valid (DD<2500) by PnL desc.
    print("\n--- TOP 10 valid (DD < $2,500) by PnL")
    valid = [(tag, x, s) for (tag, x, s) in results if s["max_dd_$"] < DD_BUDGET]
    valid.sort(key=lambda r: -r[2]["net_pnl"])
    for tag, x, s in valid[:10]:
        ratio = s["net_pnl"] / s["max_dd_$"] if s["max_dd_$"] > 0 else 0.0
        print(f"  {tag:>20s} x={x:.2f}  PnL=${s['net_pnl']:>9,.0f}  DD=${s['max_dd_$']:>6,.0f}  "
              f"P/DD={ratio:>5.2f}  N={s['trades']}")


if __name__ == "__main__":
    main()
