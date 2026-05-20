"""Phase 7 — BE / RR_TP per leg with sl_max=80 anchor.

Test:
- MGC be_at_rr: 0, 1, 1.5, 2, 2.5, 3
- MGC rr_tp: 2, 2.5, 3, 3.5, 4
- MNQ be_at_rr: 0, 1, 1.5, 2 (currently 0)
- MNQ rr_tp: 2, 2.5, 3
"""
import time
from _campaign import (
    MGC_PARAMS_BASE, MNQ_PARAMS_BASE,
    run_multi, fmt_multi,
)


def run_cfg(mgc_overrides=None, mnq_overrides=None, mgc_risk=0.0050, mnq_risk=0.0030):
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
    print("=" * 100)
    print("MGC be_at_rr sweep (MGC=0.50%, MNQ=0.30%, sl_max=80)")
    print("=" * 100)
    for be in [0, 1, 1.5, 2, 2.5, 3, 4]:
        t0 = time.time()
        s = run_cfg(mgc_overrides={"be_at_rr": be})
        dt = time.time() - t0
        print(f"MGC be_at_rr={be:<5}  {fmt_multi(s)}  ({dt:.1f}s)")

    print()
    print("=" * 100)
    print("MGC rr_tp sweep (MGC=0.50%, MNQ=0.30%, sl_max=80, be_at_rr=2)")
    print("=" * 100)
    for rr in [2.0, 2.5, 3.0, 3.5, 4.0, 5.0]:
        t0 = time.time()
        s = run_cfg(mgc_overrides={"rr_tp": rr})
        dt = time.time() - t0
        print(f"MGC rr_tp={rr:<5}  {fmt_multi(s)}  ({dt:.1f}s)")

    print()
    print("=" * 100)
    print("MNQ be_at_rr sweep (currently 0)")
    print("=" * 100)
    for be in [0, 1, 1.5, 2, 2.5, 3]:
        t0 = time.time()
        s = run_cfg(mnq_overrides={"be_at_rr": be})
        dt = time.time() - t0
        print(f"MNQ be_at_rr={be:<5}  {fmt_multi(s)}  ({dt:.1f}s)")

    print()
    print("=" * 100)
    print("MNQ rr_tp sweep (currently 2.5)")
    print("=" * 100)
    for rr in [2.0, 2.5, 3.0, 3.5, 4.0]:
        t0 = time.time()
        s = run_cfg(mnq_overrides={"rr_tp": rr})
        dt = time.time() - t0
        print(f"MNQ rr_tp={rr:<5}  {fmt_multi(s)}  ({dt:.1f}s)")


if __name__ == "__main__":
    main()
