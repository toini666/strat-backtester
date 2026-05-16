"""07 — finetune around MNQ-h08-h13 winner (P/DD=39.93)."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _campaign import (  # noqa: E402
    MGC_BASE_RISK, MNQ_BASE_RISK, base_engine_mgc, base_engine_mnq, bench,
)
from backend.api import BlackoutWindowSettings


def _add(es, sh, sm, eh, em):
    es.blackout_windows.append(BlackoutWindowSettings(
        active=True, start_hour=sh, start_minute=sm, end_hour=eh, end_minute=em))
    return es


def mnq_h08_h13() -> object:
    e = base_engine_mnq(); _add(e, 8, 0, 9, 0); _add(e, 13, 0, 14, 0); return e


def mnq_h08_h12_h13() -> object:
    e = base_engine_mnq()
    _add(e, 8, 0, 9, 0); _add(e, 12, 0, 13, 0); _add(e, 13, 0, 14, 0); return e


def mnq_h13() -> object:
    return _add(base_engine_mnq(), 13, 0, 14, 0)


def mnq_h08_h13_h04() -> object:
    e = base_engine_mnq(); _add(e, 8, 0, 9, 0); _add(e, 13, 0, 14, 0); _add(e, 4, 0, 5, 0); return e


def main() -> None:
    print(f"{'='*120}")
    print("07 — finetune MNQ h08+h13 (winner P/DD=39.93)")

    print("\n--- A. MNQ-h08+h13 base, risk variants")
    for sm in (1.00, 1.03, 1.05, 1.07, 1.08, 1.09, 1.10):
        for sg in (1.00, 1.03, 1.05):
            bench(f"h08+h13 m={sm:.2f}/g={sg:.2f}",
                  mnq_engine=mnq_h08_h13(), mnq_risk=MNQ_BASE_RISK * sm,
                  mgc_risk=MGC_BASE_RISK * sg)

    print("\n--- B. MNQ h13 alone (no h08), risk variants")
    for sm in (1.00, 1.05, 1.10):
        for sg in (1.00, 1.05):
            bench(f"h13 only m={sm:.2f}/g={sg:.2f}",
                  mnq_engine=mnq_h13(), mnq_risk=MNQ_BASE_RISK * sm,
                  mgc_risk=MGC_BASE_RISK * sg)

    print("\n--- C. Triple BO MNQ h08+h12+h13")
    for sm in (1.00, 1.05, 1.10, 1.15):
        for sg in (1.00, 1.05, 1.10):
            bench(f"h08+h12+h13 m={sm:.2f}/g={sg:.2f}",
                  mnq_engine=mnq_h08_h12_h13(), mnq_risk=MNQ_BASE_RISK * sm,
                  mgc_risk=MGC_BASE_RISK * sg)

    print("\n--- D. MNQ h08+h13+h04 (low-volume morning)")
    for sm in (1.00, 1.05, 1.10):
        for sg in (1.00, 1.05):
            bench(f"h08+h13+h04 m={sm:.2f}/g={sg:.2f}",
                  mnq_engine=mnq_h08_h13_h04(), mnq_risk=MNQ_BASE_RISK * sm,
                  mgc_risk=MGC_BASE_RISK * sg)


if __name__ == "__main__":
    main()
