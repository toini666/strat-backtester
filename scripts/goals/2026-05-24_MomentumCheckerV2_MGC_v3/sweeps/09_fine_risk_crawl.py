"""Phase 9 — Fine risk crawl around the ALT_HIGHPNL anchor.

Tests basis-point resolution around r=0.53% on the prin=18 sec=7 anchor.
Hunting for a higher-PnL cell that doesn't bust DD.
"""
from __future__ import annotations

import sys
from pathlib import Path

CAMPAIGN = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CAMPAIGN / "sweeps"))

from _helper import bench  # type: ignore


def header(t):
    print("\n" + "=" * 78)
    print(f"  {t}")
    print("=" * 78)


def main():
    header("Phase 9a — Fine risk crawl on prin=18 sec=7 sl_max=120")
    base = {"ema_prin_len": 18, "ema_sec_len": 7, "sl_max_points": 120.0}
    for r in [0.0053, 0.0054, 0.0055, 0.0056, 0.0057, 0.0058, 0.0060, 0.0062, 0.0065, 0.0070]:
        bench(f"r={r*100:.3f}% prin=18 sec=7", params=base, risk_per_trade=r)

    header("Phase 9b — Fine risk crawl on prin=15 sec=7 (WR anchor)")
    base = {"ema_prin_len": 15, "ema_sec_len": 7, "sl_max_points": 120.0}
    for r in [0.0053, 0.0054, 0.0055, 0.0056, 0.0057, 0.0058, 0.0060]:
        bench(f"r={r*100:.3f}% prin=15 sec=7", params=base, risk_per_trade=r)

    header("Phase 9c — Seed anchor fine risk crawl (for strict WINNER)")
    base = {"sl_max_points": 120.0}
    for r in [0.0050, 0.0051, 0.0052, 0.0053, 0.0054, 0.0055, 0.0056, 0.0058]:
        bench(f"r={r*100:.3f}% seed+sl_max=120", params=base, risk_per_trade=r)


if __name__ == "__main__":
    main()
