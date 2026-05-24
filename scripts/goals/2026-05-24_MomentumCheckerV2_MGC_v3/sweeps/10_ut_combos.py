"""Phase 10 — UT_on combos with other survivors.

UT ON key=1.5 atr=10 alone gives +$1,679 / +$27 DD on seed.
Test combinations with sl_max=120 and ema_prin family.
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
    header("Phase 10a — UT ON × seed + sl_max=120")
    for key, atr in [(1.5, 10), (1.5, 14), (1.5, 7), (1.0, 14), (2.0, 10), (2.0, 14)]:
        bench(
            f"UT k={key} atr={atr} + sl_max=120",
            params={"ut_on": True, "ut_key": key, "ut_atr_period": atr,
                    "sl_max_points": 120.0},
        )

    header("Phase 10b — UT ON × ema_prin combos")
    for prin in [15, 18, 30]:
        for sec in [5, 7]:
            bench(
                f"UT k=1.5 atr=10 + prin={prin} sec={sec}",
                params={"ut_on": True, "ut_key": 1.5, "ut_atr_period": 10,
                        "ema_prin_len": prin, "ema_sec_len": sec,
                        "sl_max_points": 120.0},
            )

    header("Phase 10c — UT ON fine key sweep (1.4-1.6)")
    for k in [1.3, 1.4, 1.5, 1.6, 1.7, 1.8]:
        bench(
            f"UT k={k} atr=10 + sl_max=120",
            params={"ut_on": True, "ut_key": k, "ut_atr_period": 10,
                    "sl_max_points": 120.0},
        )

    header("Phase 10d — UT ON × risk crawl on best anchor")
    base = {"ut_on": True, "ut_key": 1.5, "ut_atr_period": 10, "sl_max_points": 120.0}
    for r in [0.0050, 0.0052, 0.0053, 0.0055, 0.0057, 0.0060]:
        bench(f"r={r*100:.3f}% UT base", params=base, risk_per_trade=r)


if __name__ == "__main__":
    main()
