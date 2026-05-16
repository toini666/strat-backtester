"""10 — final validation: winner + 5 alternatives (re-run to confirm replay determinism)."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _campaign import (  # noqa: E402
    MGC_BASE_RISK, MNQ_BASE_RISK, base_engine_mnq, bench,
)
from backend.api import BlackoutWindowSettings


def _add(es, sh, sm, eh, em):
    es.blackout_windows.append(BlackoutWindowSettings(
        active=True, start_hour=sh, start_minute=sm, end_hour=eh, end_minute=em))
    return es


def mnq_3bo() -> object:
    e = base_engine_mnq()
    _add(e, 8, 0, 9, 0); _add(e, 12, 0, 13, 0); _add(e, 13, 0, 14, 0); return e


def main() -> None:
    print(f"{'='*120}")
    print("10 — FINAL VALIDATION: re-run winners to confirm replay determinism\n")

    print("--- WINNER candidate")
    bench("[WINNER] 3BO m=1.04/g=1.15",
          mnq_engine=mnq_3bo(),
          mnq_risk=MNQ_BASE_RISK * 1.04, mgc_risk=MGC_BASE_RISK * 1.15)

    print("\n--- ALTERNATIVES (close to winner)")
    bench("[ALT1]   3BO m=1.04/g=1.14",
          mnq_engine=mnq_3bo(),
          mnq_risk=MNQ_BASE_RISK * 1.04, mgc_risk=MGC_BASE_RISK * 1.14)
    bench("[ALT2]   3BO m=1.04/g=1.13",
          mnq_engine=mnq_3bo(),
          mnq_risk=MNQ_BASE_RISK * 1.04, mgc_risk=MGC_BASE_RISK * 1.13)
    bench("[ALT3]   3BO m=1.03/g=1.15",
          mnq_engine=mnq_3bo(),
          mnq_risk=MNQ_BASE_RISK * 1.03, mgc_risk=MGC_BASE_RISK * 1.15)
    bench("[ALT4]   3BO m=1.04/g=1.10",
          mnq_engine=mnq_3bo(),
          mnq_risk=MNQ_BASE_RISK * 1.04, mgc_risk=MGC_BASE_RISK * 1.10)
    bench("[ALT5]   3BO m=1.04/g=1.17",
          mnq_engine=mnq_3bo(),
          mnq_risk=MNQ_BASE_RISK * 1.04, mgc_risk=MGC_BASE_RISK * 1.17)


if __name__ == "__main__":
    main()
