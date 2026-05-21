"""Phase 00 — Baseline. Replay the COMBO RIsky preset exactly to anchor PnL/DD."""
from __future__ import annotations

from _campaign import fmt_multi, run_multi, INITIAL_EQUITY  # noqa: E402

if __name__ == "__main__":
    print(f"INITIAL EQUITY: ${INITIAL_EQUITY:,.0f}")
    s = run_multi()
    print("\nBASELINE COMBO RIsky preset:")
    print(f"  {fmt_multi(s)}")
    print(f"  max_dd_% = {s['max_dd_%']:.2f}%")
    print(f"  DD peak  : {s['dd_peak_time']}")
    print(f"  DD trough: {s['dd_trough_time']}")
