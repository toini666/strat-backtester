"""Phase 13 — final refine to confirm winner at $88k+ / DD ≤ $2,300.

Best so far: MGC=0.50%/be2.0 mcp=0.25 sl_max=80 + MNQ=0.35%/be2.0 → $88,022/$2,292.
Margin: only $8. Need to verify robustness and explore tiny tweaks.

Test:
- MNQ_be 2.4-2.7 at MGC=0.50%/MNQ=0.35% mcp=0.25 (higher BE = more BE saves)
- MNQ risk 0.34-0.38 (fine grid around 0.35%)
- mcp 0.23-0.27 around 0.25 sweet spot
- be_mgc 1.9-2.1
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

    # Anchor: MGC=0.50%/be2.0 mcp=0.25 + MNQ=0.35%/be2.0 (winner candidate)
    anchor_label = "ANCHOR: MGC=0.50%/be2.0 mcp=0.25 MNQ=0.35%/be2.0"
    s = run_cfg(
        mgc_risk=0.0050, mnq_risk=0.0035,
        mgc_overrides={"max_candle_pct": 0.25, "be_at_rr": 2.0},
        mnq_overrides={"be_at_rr": 2.0},
    )
    print(f"{anchor_label:<55s} {fmt_multi(s)}")
    rows.append((anchor_label, s))
    print()

    print("=" * 110)
    print("A) MNQ_be high values (2.4-2.7) at MGC=0.50%/MNQ=0.35%")
    print("=" * 110)
    for mnq_be in [2.4, 2.5, 2.6, 2.7]:
        t0 = time.time()
        s = run_cfg(
            mgc_risk=0.0050, mnq_risk=0.0035,
            mgc_overrides={"max_candle_pct": 0.25, "be_at_rr": 2.0},
            mnq_overrides={"be_at_rr": mnq_be},
        )
        dt = time.time() - t0
        label = f"MNQ_be={mnq_be}"
        print(f"{label:<55s} {fmt_multi(s)}  ({dt:.1f}s)")
        rows.append((label, s))

    print()
    print("=" * 110)
    print("B) MNQ risk fine grid 0.33-0.38 at MGC=0.50% mcp=0.25 MNQ_be=2.0")
    print("=" * 110)
    for mnq_r in [0.0033, 0.0034, 0.0036, 0.0037, 0.0038]:
        t0 = time.time()
        s = run_cfg(
            mgc_risk=0.0050, mnq_risk=mnq_r,
            mgc_overrides={"max_candle_pct": 0.25, "be_at_rr": 2.0},
            mnq_overrides={"be_at_rr": 2.0},
        )
        dt = time.time() - t0
        label = f"MNQ={mnq_r*100:.2f}%"
        print(f"{label:<55s} {fmt_multi(s)}  ({dt:.1f}s)")
        rows.append((label, s))

    print()
    print("=" * 110)
    print("C) mcp fine 0.23/0.24/0.26/0.27")
    print("=" * 110)
    for mcp in [0.23, 0.24, 0.26, 0.27]:
        t0 = time.time()
        s = run_cfg(
            mgc_risk=0.0050, mnq_risk=0.0035,
            mgc_overrides={"max_candle_pct": mcp, "be_at_rr": 2.0},
            mnq_overrides={"be_at_rr": 2.0},
        )
        dt = time.time() - t0
        label = f"mcp={mcp}"
        print(f"{label:<55s} {fmt_multi(s)}  ({dt:.1f}s)")
        rows.append((label, s))

    print()
    print("=" * 110)
    print("D) MGC risk 0.48-0.52 fine grid")
    print("=" * 110)
    for mgc_r in [0.0048, 0.0049, 0.0051, 0.0052]:
        t0 = time.time()
        s = run_cfg(
            mgc_risk=mgc_r, mnq_risk=0.0035,
            mgc_overrides={"max_candle_pct": 0.25, "be_at_rr": 2.0},
            mnq_overrides={"be_at_rr": 2.0},
        )
        dt = time.time() - t0
        label = f"MGC={mgc_r*100:.2f}%"
        print(f"{label:<55s} {fmt_multi(s)}  ({dt:.1f}s)")
        rows.append((label, s))

    print()
    print("=" * 110)
    print("ALL configs under DD ≤ $2,300 sorted by PnL")
    print("=" * 110)
    under = [r for r in rows if r[1]["max_dd_$"] <= 2300]
    for label, s in sorted(under, key=lambda r: -r[1]["net_pnl"])[:15]:
        flag = "🎯" if s["max_dd_$"] <= 2000 else "✅"
        margin = 2300 - s["max_dd_$"]
        print(f"  {flag} {label:<55s} PnL=${s['net_pnl']:>9,.0f} "
              f"DD=${s['max_dd_$']:>6,.0f}  margin=${margin:>5,.0f}")


if __name__ == "__main__":
    main()
