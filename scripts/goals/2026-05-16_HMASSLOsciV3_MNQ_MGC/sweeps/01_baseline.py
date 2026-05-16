"""01_baseline — replay the saved preset and record combined PnL/DD."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _campaign import bench, DD_BUDGET, PNL_TARGET  # noqa: E402


def main() -> None:
    print(f"{'='*120}")
    print(f"Campaign: HMASSLOsciV3 multi-asset MNQ + MGC")
    print(f"Targets : PnL > ${PNL_TARGET:,.0f}  |  DD < ${DD_BUDGET:,.0f}")
    print(f"{'='*120}\n")

    print("Baseline replay — preset 'HMA-SSL-V3 - MNQ/MGC - Best':")
    s = bench("baseline (preset)")

    print()
    print(f"Per-leg snapshot:")
    print(f"  MNQ leg: ${s['mnq_pnl']:>+9,.0f}  N={s['mnq_trades']}")
    print(f"  MGC leg: ${s['mgc_pnl']:>+9,.0f}  N={s['mgc_trades']}")
    print(f"  Combined PnL: ${s['net_pnl']:>+9,.0f}")
    print(f"  Combined DD$: ${s['max_dd_$']:>9,.0f}  (margin ${DD_BUDGET - s['max_dd_$']:+,.0f})")
    print(f"  Ratio P/DD : {s['net_pnl'] / s['max_dd_$']:.2f}")


if __name__ == "__main__":
    main()
