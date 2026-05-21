"""Phase 06 — MNQ blackout extension around the DD cluster.

DD episode trace: MNQ had 3 consecutive -$250 losses on 04-23 at 15:17,
15:38, 16:48 (US session open, before MNQ's 17:00 blackout). Extending
MNQ's earlier blackout to 17:00 may kill that mini-streak.

We test candidates that fold 14:30-17:00 (or chunks of it) into the
existing 13:00-14:30 window.
"""
from __future__ import annotations

from _campaign import MGC_BLACKOUTS_BASE, MNQ_RISK_BASE, fmt_multi, run_multi  # noqa: E402

# Variants of MNQ blackouts. Base = (9,0,10,0), (13,0,14,30), (17,0,23,59), (22,0,23,59)
VARIANTS = {
    "base": [
        (9, 0, 10, 0), (13, 0, 14, 30), (17, 0, 23, 59), (22, 0, 23, 59),
    ],
    "extend-to-17":  [
        (9, 0, 10, 0), (13, 0, 17, 0), (17, 0, 23, 59), (22, 0, 23, 59),
    ],
    "extend-15-17": [
        (9, 0, 10, 0), (13, 0, 14, 30), (15, 0, 17, 0),
        (17, 0, 23, 59), (22, 0, 23, 59),
    ],
    "extend-1530-17": [
        (9, 0, 10, 0), (13, 0, 14, 30), (15, 30, 17, 0),
        (17, 0, 23, 59), (22, 0, 23, 59),
    ],
    "extend-1500-1700+0930": [
        (9, 0, 10, 0), (9, 30, 10, 30),
        (13, 0, 14, 30), (15, 0, 17, 0),
        (17, 0, 23, 59), (22, 0, 23, 59),
    ],
}

if __name__ == "__main__":
    print(f"MNQ blackout variants at MNQ risk={MNQ_RISK_BASE:.4f} (MGC unchanged):\n")
    rows = []
    for name, bo in VARIANTS.items():
        s = run_multi(mnq_blackouts=bo, mgc_blackouts=MGC_BLACKOUTS_BASE)
        marker = " ✓" if s["max_dd_$"] < 2500 else ""
        print(f"  {name:<24s}  {fmt_multi(s)}{marker}")
        rows.append((name, s))
