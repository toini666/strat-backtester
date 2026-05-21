"""Phase 04 — MGC risk sweep at base MNQ.

Find MGC rounding cells. Prior combo found 0.53 % was favorable; verify here.
"""
from __future__ import annotations

from _campaign import MNQ_RISK_BASE, fmt_multi, run_multi  # noqa: E402

RISKS = [0.0060, 0.0055, 0.0053, 0.0050, 0.0048, 0.0045, 0.0042, 0.0040, 0.0036, 0.0033, 0.0030]

if __name__ == "__main__":
    print(f"MGC risk sweep at MNQ risk={MNQ_RISK_BASE:.4f}:\n")
    for r in RISKS:
        s = run_multi(mgc_risk=r)
        marker = "  ✓" if s["max_dd_$"] < 2500 else ""
        print(f"  MGC_risk={r:.4f}  {fmt_multi(s)}{marker}")
