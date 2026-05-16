"""09 — micro finetune around m=1.04/g=1.10 winner. Explore g>1.12 and m=1.03-1.05."""
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
    print("09 — micro-finetune around winner zone\n")

    print("--- A. m ∈ {1.03, 1.04, 1.05} × g ∈ {1.10..1.20}")
    for sm_pct in (103, 104, 105):
        for sg_pct in (110, 111, 113, 114, 115, 117, 120):
            sm = sm_pct / 100
            sg = sg_pct / 100
            bench(f"3BO m={sm:.2f}/g={sg:.2f}",
                  mnq_engine=mnq_3bo(), mnq_risk=MNQ_BASE_RISK * sm,
                  mgc_risk=MGC_BASE_RISK * sg)

    print("\n--- B. m ∈ {1.06, 1.08, 1.10, 1.12} × g ∈ {1.05, 1.08, 1.10, 1.12, 1.15}")
    for sm_pct in (106, 108, 110, 112):
        for sg_pct in (105, 108, 110, 112, 115):
            sm = sm_pct / 100
            sg = sg_pct / 100
            bench(f"3BO m={sm:.2f}/g={sg:.2f}",
                  mnq_engine=mnq_3bo(), mnq_risk=MNQ_BASE_RISK * sm,
                  mgc_risk=MGC_BASE_RISK * sg)


if __name__ == "__main__":
    main()
