"""Phase 9 — Pareto fine-tune.

Phase 8 best PnL under $2,300: MGC=0.40% MNQ=0.35% be=2.0 → $82,169 / $2,292.
Near-miss: MGC=0.50% MNQ=0.35% be=2.0 → $87,906 / $2,380 (only $80 over).
And: MGC=0.55% MNQ=0.30% be=2.0 → $86,789 / $2,490 (over by $190).

Strategy: find small tweaks that pull DD below $2,300 while keeping PnL high.

Test:
1. MNQ be_at_rr fractional values (1.7, 1.8, 1.9, 2.1, 2.2) at top configs
2. MGC max_candle_pct=0.25, 0.20 (already tested in mono-asset but may differ in combined)
3. MGC sl_lookback variations
4. Lower risks for sub-$2,000 push
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
    print("A) MNQ be_at_rr fine sweep — MGC=0.50%/0.55%, MNQ=0.30%/0.35%")
    print("=" * 110)
    for mgc_r, mnq_r in [(0.0050, 0.0035), (0.0055, 0.0030), (0.0050, 0.0040)]:
        for be in [1.6, 1.7, 1.8, 1.9, 2.0, 2.1, 2.2, 2.3]:
            t0 = time.time()
            s = run_cfg(mgc_risk=mgc_r, mnq_risk=mnq_r,
                        mnq_overrides={"be_at_rr": be})
            dt = time.time() - t0
            label = f"MGC={mgc_r*100:.2f}% MNQ={mnq_r*100:.2f}% be={be}"
            print(f"{label:<40s} {fmt_multi(s)}  ({dt:.1f}s)")
            rows.append((label, s))

    print()
    print("=" * 110)
    print("B) MGC max_candle_pct lower (currently 0.30) — anchor MGC=0.50%/MNQ=0.35% be=2.0")
    print("=" * 110)
    for mcp in [0.20, 0.22, 0.25, 0.28, 0.30, 0.35]:
        t0 = time.time()
        s = run_cfg(
            mgc_risk=0.0050, mnq_risk=0.0035,
            mgc_overrides={"max_candle_pct": mcp},
            mnq_overrides={"be_at_rr": 2.0},
        )
        dt = time.time() - t0
        label = f"MGC mcp={mcp}"
        print(f"{label:<40s} {fmt_multi(s)}  ({dt:.1f}s)")
        rows.append((label, s))

    print()
    print("=" * 110)
    print("C) MGC sl_lookback (currently 15) — anchor MGC=0.50%/MNQ=0.35% be=2.0")
    print("=" * 110)
    for sll in [10, 12, 15, 18, 20]:
        t0 = time.time()
        s = run_cfg(
            mgc_risk=0.0050, mnq_risk=0.0035,
            mgc_overrides={"sl_lookback": sll},
            mnq_overrides={"be_at_rr": 2.0},
        )
        dt = time.time() - t0
        label = f"MGC sl_lookback={sll}"
        print(f"{label:<40s} {fmt_multi(s)}  ({dt:.1f}s)")
        rows.append((label, s))

    print()
    print("=" * 110)
    print("D) MGC be_at_rr variations (currently 2) — anchor MGC=0.50%/MNQ=0.35% be=2.0")
    print("=" * 110)
    for mbe in [1.0, 1.5, 1.8, 2.0, 2.2, 2.5, 3.0]:
        t0 = time.time()
        s = run_cfg(
            mgc_risk=0.0050, mnq_risk=0.0035,
            mgc_overrides={"be_at_rr": mbe},
            mnq_overrides={"be_at_rr": 2.0},
        )
        dt = time.time() - t0
        label = f"MGC be={mbe}"
        print(f"{label:<40s} {fmt_multi(s)}  ({dt:.1f}s)")
        rows.append((label, s))

    print()
    print("=" * 110)
    print("Top PnL configs under DD ≤ $2,300")
    print("=" * 110)
    under = [r for r in rows if r[1]["max_dd_$"] <= 2300]
    for label, s in sorted(under, key=lambda r: -r[1]["net_pnl"])[:15]:
        flag = "🎯" if s["max_dd_$"] <= 2000 else "✅"
        print(f"  {flag} {label:<45s} PnL=${s['net_pnl']:>9,.0f} DD=${s['max_dd_$']:>6,.0f}")

    print()
    print("=" * 110)
    print("Near-miss $2,300-$2,500 (high-PnL candidates if one more lever can shave DD)")
    print("=" * 110)
    near = [r for r in rows if 2300 < r[1]["max_dd_$"] <= 2500]
    for label, s in sorted(near, key=lambda r: -r[1]["net_pnl"])[:10]:
        gap = s["max_dd_$"] - 2300
        print(f"  ⚠️  {label:<45s} PnL=${s['net_pnl']:>9,.0f} DD=${s['max_dd_$']:>6,.0f}  (over by ${gap:+,.0f})")


if __name__ == "__main__":
    main()
