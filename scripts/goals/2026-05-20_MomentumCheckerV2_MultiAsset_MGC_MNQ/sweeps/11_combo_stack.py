"""Phase 11 — stack winning levers.

Top levers from Phase 9:
- MGC mcp=0.25 → $88,022/$2,292 (vs mcp=0.30 → $87,906/$2,380)
- MGC be=1.8 → $87,898/$2,292 (DD-only lever, tiny PnL gain)
- MNQ_be=2.3 + MNQ=0.40% → $95,103/$2,505 (high PnL, $205 over $2,300)

Test:
- Stack mcp=0.25 + be_mgc=1.8 (interaction)
- mcp=0.25 + MNQ_be=2.0-2.3 + MNQ risk 0.30-0.45%
- Push MGC risk to 0.55%
- Sub-$2,000 alternative — find best PnL there
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
    print("A) Stack mcp=0.25 + be_mgc=1.8 + MNQ_be variations × MGC/MNQ risks")
    print("=" * 110)
    for mgc_r in [0.0050, 0.0055]:
        for mnq_r in [0.0030, 0.0035, 0.0040, 0.0045]:
            for be_mgc in [1.8, 2.0]:
                for mnq_be in [2.0, 2.1, 2.2, 2.3]:
                    t0 = time.time()
                    s = run_cfg(
                        mgc_risk=mgc_r, mnq_risk=mnq_r,
                        mgc_overrides={"max_candle_pct": 0.25, "be_at_rr": be_mgc},
                        mnq_overrides={"be_at_rr": mnq_be},
                    )
                    dt = time.time() - t0
                    label = f"MGC={mgc_r*100:.2f}%/be{be_mgc} MNQ={mnq_r*100:.2f}%/be{mnq_be}"
                    print(f"{label:<45s} {fmt_multi(s)}  ({dt:.1f}s)")
                    rows.append((label, s))

    print()
    print("=" * 110)
    print("B) Sub-$2,000 push — low risks with mcp=0.25 + be_mgc=1.8")
    print("=" * 110)
    for mgc_r in [0.0030, 0.0035, 0.0040, 0.0045, 0.0050]:
        for mnq_r in [0.0015, 0.0020, 0.0025, 0.0030]:
            for mnq_be in [1.5, 2.0]:
                t0 = time.time()
                s = run_cfg(
                    mgc_risk=mgc_r, mnq_risk=mnq_r,
                    mgc_overrides={"max_candle_pct": 0.25, "be_at_rr": 1.8},
                    mnq_overrides={"be_at_rr": mnq_be},
                )
                dt = time.time() - t0
                label = f"MGC={mgc_r*100:.2f}% MNQ={mnq_r*100:.2f}% mnq_be={mnq_be}"
                print(f"{label:<45s} {fmt_multi(s)}  ({dt:.1f}s)")
                rows.append((label, s))

    print()
    print("=" * 110)
    print("TOP under DD ≤ $2,300 (winner candidates) — sorted by PnL")
    print("=" * 110)
    under_hard = [r for r in rows if r[1]["max_dd_$"] <= 2300]
    for label, s in sorted(under_hard, key=lambda r: -r[1]["net_pnl"])[:20]:
        flag = "🎯" if s["max_dd_$"] <= 2000 else "✅"
        print(f"  {flag} {label:<48s} PnL=${s['net_pnl']:>9,.0f} DD=${s['max_dd_$']:>6,.0f} "
              f"P/DD={s['net_pnl']/max(s['max_dd_$'],1):>5.1f}")

    print()
    print("=" * 110)
    print("Sub-$2,000 candidates — sorted by PnL")
    print("=" * 110)
    under_soft = [r for r in rows if r[1]["max_dd_$"] <= 2000]
    for label, s in sorted(under_soft, key=lambda r: -r[1]["net_pnl"])[:10]:
        print(f"  🎯 {label:<48s} PnL=${s['net_pnl']:>9,.0f} DD=${s['max_dd_$']:>6,.0f}")


if __name__ == "__main__":
    main()
