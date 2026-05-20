"""Phase 0 — baseline. Replay the user's preset exactly and record the
combined max_dd_$ and PnL. This is the anchor we measure against.
"""
import time
from _campaign import (
    MGC_PARAMS_BASE, MNQ_PARAMS_BASE,
    MGC_BLACKOUTS_BASE, MNQ_BLACKOUTS_BASE,
    run_multi, fmt_multi,
)


def main():
    t0 = time.time()
    s = run_multi(
        mgc_params=MGC_PARAMS_BASE, mgc_risk=0.0055,
        mgc_blackouts=MGC_BLACKOUTS_BASE,
        mnq_params=MNQ_PARAMS_BASE, mnq_risk=0.0066,
        mnq_blackouts=MNQ_BLACKOUTS_BASE,
    )
    dt = time.time() - t0
    print(f"{'BASELINE preset (MGC 0.55%, MNQ 0.66%)':<55s} {fmt_multi(s)}  ({dt:.1f}s)")
    print()
    print("Reference targets:")
    print(f"  - HARD ceiling : DD < $2,300  (current = ${s['max_dd_$']:,.0f}, gap = ${s['max_dd_$']-2300:+,.0f})")
    print(f"  - SOFT target  : DD < $2,000  (current = ${s['max_dd_$']:,.0f}, gap = ${s['max_dd_$']-2000:+,.0f})")


if __name__ == "__main__":
    main()
