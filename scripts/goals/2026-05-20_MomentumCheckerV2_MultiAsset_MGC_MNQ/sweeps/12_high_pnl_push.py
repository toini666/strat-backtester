"""Phase 12 — push PnL higher at MGC=0.55% by shaving DD.

Phase 11 near-misses:
- MGC=0.55%/be2.0 MNQ=0.45%/be2.3 mcp=0.25 → $105,097 / $2,658 (over by $358)
- MGC=0.55%/be2.0 MNQ=0.40%/be2.3 mcp=0.25 → $101,207 / $2,476 (over by $176)

Try aggressive mcp variations + sl_max variations on top of MGC=0.55%.
Also try sub-$2,000 push with extreme MGC levers (mostly expected to fail).
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
    print("A) MGC=0.55% × mcp variations × MNQ risks @ MNQ_be=2.3")
    print("=" * 110)
    for mcp in [0.18, 0.20, 0.22, 0.25, 0.28]:
        for mnq_r in [0.0035, 0.0040, 0.0045]:
            for be_mgc in [1.8, 2.0]:
                t0 = time.time()
                s = run_cfg(
                    mgc_risk=0.0055, mnq_risk=mnq_r,
                    mgc_overrides={"max_candle_pct": mcp, "be_at_rr": be_mgc},
                    mnq_overrides={"be_at_rr": 2.3},
                )
                dt = time.time() - t0
                label = f"MGC mcp={mcp}/be{be_mgc} MNQ={mnq_r*100:.2f}%"
                print(f"{label:<45s} {fmt_multi(s)}  ({dt:.1f}s)")
                rows.append((label, s))

    print()
    print("=" * 110)
    print("B) MGC=0.55% with tighter MGC sl_max (60, 70) — anchor MNQ=0.40%/be2.3")
    print("=" * 110)
    for sl_max in [50, 60, 70, 90]:
        for mcp in [0.22, 0.25]:
            t0 = time.time()
            s = run_cfg(
                mgc_risk=0.0055, mnq_risk=0.0040,
                mgc_overrides={"max_candle_pct": mcp, "be_at_rr": 2.0,
                               "sl_max_points": sl_max},
                mnq_overrides={"be_at_rr": 2.3},
            )
            dt = time.time() - t0
            label = f"MGC sl_max={sl_max}/mcp={mcp}"
            print(f"{label:<45s} {fmt_multi(s)}  ({dt:.1f}s)")
            rows.append((label, s))

    print()
    print("=" * 110)
    print("C) Sub-$2,000 aggressive — be_mgc=1.5, very low risks")
    print("=" * 110)
    for be_mgc in [1.0, 1.3, 1.5]:
        for mgc_r in [0.0030, 0.0040, 0.0050]:
            for mnq_r, mnq_be in [(0.0020, 2.0), (0.0030, 2.0), (0.0030, 1.5)]:
                t0 = time.time()
                s = run_cfg(
                    mgc_risk=mgc_r, mnq_risk=mnq_r,
                    mgc_overrides={"max_candle_pct": 0.25, "be_at_rr": be_mgc},
                    mnq_overrides={"be_at_rr": mnq_be},
                )
                dt = time.time() - t0
                label = f"MGC={mgc_r*100:.2f}%/be{be_mgc} MNQ={mnq_r*100:.2f}%/be{mnq_be}"
                print(f"{label:<48s} {fmt_multi(s)}  ({dt:.1f}s)")
                rows.append((label, s))

    print()
    print("=" * 110)
    print("TOP under DD ≤ $2,300 — sorted by PnL")
    print("=" * 110)
    under_hard = [r for r in rows if r[1]["max_dd_$"] <= 2300]
    for label, s in sorted(under_hard, key=lambda r: -r[1]["net_pnl"])[:15]:
        flag = "🎯" if s["max_dd_$"] <= 2000 else "✅"
        print(f"  {flag} {label:<48s} PnL=${s['net_pnl']:>9,.0f} DD=${s['max_dd_$']:>6,.0f}")

    print()
    print("=" * 110)
    print("Sub-$2,000 — sorted by PnL")
    print("=" * 110)
    under_soft = [r for r in rows if r[1]["max_dd_$"] <= 2000]
    for label, s in sorted(under_soft, key=lambda r: -r[1]["net_pnl"])[:10]:
        print(f"  🎯 {label:<48s} PnL=${s['net_pnl']:>9,.0f} DD=${s['max_dd_$']:>6,.0f}")


if __name__ == "__main__":
    main()
