"""Phase 14 — final micro-combos. Try to stack:
- mcp=0.26 (PnL +$305 over mcp=0.25 at same DD)
- MGC risk variations 0.48-0.52
- MNQ_be 2.0/2.4 (2.4 gives +$5k PnL for $34 more DD)
- MNQ risk 0.33-0.37
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
    print("Micro-combos around MNQ_be=2.4 + mcp tweaks + risk tweaks")
    print("=" * 110)

    # Test: with MNQ_be=2.4 (over by $26), tweak other levers to shave DD
    tests = [
        # (label, mgc_r, mnq_r, mcp, be_mgc, mnq_be)
        ("M_be24 mcp=0.25", 0.0050, 0.0035, 0.25, 2.0, 2.4),
        ("M_be24 mcp=0.26", 0.0050, 0.0035, 0.26, 2.0, 2.4),
        ("M_be24 mcp=0.27", 0.0050, 0.0035, 0.27, 2.0, 2.4),
        ("M_be24 MGC=0.49%", 0.0049, 0.0035, 0.25, 2.0, 2.4),
        ("M_be24 MGC=0.48%", 0.0048, 0.0035, 0.25, 2.0, 2.4),
        ("M_be24 MGC=0.49% mcp=0.26", 0.0049, 0.0035, 0.26, 2.0, 2.4),
        ("M_be24 MNQ=0.34%", 0.0050, 0.0034, 0.25, 2.0, 2.4),
        ("M_be24 MNQ=0.33%", 0.0050, 0.0033, 0.25, 2.0, 2.4),
        ("M_be24 MNQ=0.36%", 0.0050, 0.0036, 0.25, 2.0, 2.4),
        ("M_be24 be_mgc=1.8", 0.0050, 0.0035, 0.25, 1.8, 2.4),
        ("M_be24 be_mgc=1.9", 0.0050, 0.0035, 0.25, 1.9, 2.4),
        ("M_be24 be_mgc=2.1", 0.0050, 0.0035, 0.25, 2.1, 2.4),
        # Stack: mcp=0.26 + MGC=0.49% + MNQ_be=2.4
        ("STACK mcp=0.26+MGC=0.49%+MNQ_be=2.4", 0.0049, 0.0035, 0.26, 2.0, 2.4),
        ("STACK mcp=0.26+MGC=0.48%+MNQ_be=2.4", 0.0048, 0.0035, 0.26, 2.0, 2.4),
    ]

    for label, mgc_r, mnq_r, mcp, be_mgc, mnq_be in tests:
        t0 = time.time()
        s = run_cfg(
            mgc_risk=mgc_r, mnq_risk=mnq_r,
            mgc_overrides={"max_candle_pct": mcp, "be_at_rr": be_mgc},
            mnq_overrides={"be_at_rr": mnq_be},
        )
        dt = time.time() - t0
        print(f"{label:<45s} {fmt_multi(s)}  ({dt:.1f}s)")
        rows.append((label, s))

    print()
    print("=" * 110)
    print("FINAL TOP under $2,300 sorted by PnL")
    print("=" * 110)
    under = [r for r in rows if r[1]["max_dd_$"] <= 2300]
    for label, s in sorted(under, key=lambda r: -r[1]["net_pnl"])[:15]:
        margin = 2300 - s["max_dd_$"]
        print(f"  ✅ {label:<45s} PnL=${s['net_pnl']:>9,.0f} DD=${s['max_dd_$']:>6,.0f}  margin=${margin:>5,.0f}")

    print()
    print("=" * 110)
    print("Near-miss $2,300-$2,400 (lots of PnL just over)")
    print("=" * 110)
    near = [r for r in rows if 2300 < r[1]["max_dd_$"] <= 2400]
    for label, s in sorted(near, key=lambda r: -r[1]["net_pnl"])[:10]:
        gap = s["max_dd_$"] - 2300
        print(f"  ⚠️  {label:<45s} PnL=${s['net_pnl']:>9,.0f} DD=${s['max_dd_$']:>6,.0f}  over by ${gap:>4,.0f}")


if __name__ == "__main__":
    main()
