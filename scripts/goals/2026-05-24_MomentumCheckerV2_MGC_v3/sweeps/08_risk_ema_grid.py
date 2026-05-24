"""Phase 8 — risk × ema_prin × ema_sec critical grid.

The discriminating question: does lower risk + ema_prin=15/18 land any cell
at DD ≤ $2,135 with PnL > $56,275 (seed)? If yes → strict WINNER.
If no → ship ALT_HIGHPNL at higher DD.

Also spot-checks the be=0 × high-WR cell.
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
    header("Phase 8a — risk × (ema_prin, ema_sec) — DD-rounding cell hunt")
    for risk_pct in [0.0045, 0.0048, 0.0050, 0.0052, 0.0053]:
        for prin in [15, 18]:
            for sec in [5, 7, 9]:
                bench(
                    f"r={risk_pct*100:.3f}% prin={prin} sec={sec}",
                    params={"ema_prin_len": prin, "ema_sec_len": sec,
                            "sl_max_points": 120.0},
                    risk_per_trade=risk_pct,
                )

    header("Phase 8b — be=0 × prin=15 × risk crawl (high WR investigation)")
    for risk_pct in [0.0040, 0.0045, 0.0048, 0.0050, 0.0053]:
        bench(
            f"r={risk_pct*100:.3f}% be=0 prin=15",
            params={"ema_prin_len": 15, "ema_sec_len": 7, "sl_max_points": 120.0,
                    "be_at_rr": 0.0},
            risk_per_trade=risk_pct,
        )


if __name__ == "__main__":
    main()
