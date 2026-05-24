"""Phase 5 spot-check — UT_on toggle + a few module sweeps.

Per advisor: MGC v2 already exhausted these modules. Only spot-check the
unknown: UT_on=True (currently OFF in seed).
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
    header("Phase 5 spot-check — UT_on toggle (seed: OFF)")
    for k in [0.5, 1.0, 1.5]:
        for a in [7, 10, 14]:
            bench(
                f"UT ON key={k} atr={a}",
                params={"ut_on": True, "ut_key": k, "ut_atr_period": a},
            )

    header("Phase 5 spot-check — st_atr / stc_length")
    for v in [14]:
        bench(f"st_atr={v}", params={"st_atr": v})
    for v in [12]:
        bench(f"stc_length={v}", params={"stc_length": v})


if __name__ == "__main__":
    main()
