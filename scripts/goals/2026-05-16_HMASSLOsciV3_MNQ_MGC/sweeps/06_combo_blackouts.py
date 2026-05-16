"""06 — combine the best MNQ BO (h08-09) with MGC BO variants and risk tweaks."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _campaign import (  # noqa: E402
    MGC_BASE_RISK, MNQ_BASE_RISK, base_engine_mgc, base_engine_mnq, bench,
)
from backend.api import BlackoutWindowSettings


def _add_bo(es, sh, sm, eh, em):
    es.blackout_windows.append(BlackoutWindowSettings(
        active=True, start_hour=sh, start_minute=sm, end_hour=eh, end_minute=em))
    return es


def mnq_h08() -> object:
    return _add_bo(base_engine_mnq(), 8, 0, 9, 0)


def mnq_h08_h12() -> object:
    e = base_engine_mnq()
    _add_bo(e, 8, 0, 9, 0)
    _add_bo(e, 12, 0, 13, 0)
    return e


def mnq_h08_h13() -> object:
    e = base_engine_mnq()
    _add_bo(e, 8, 0, 9, 0)
    _add_bo(e, 13, 0, 14, 0)
    return e


def mgc_h17() -> object:
    return _add_bo(base_engine_mgc(), 17, 0, 18, 0)


def mgc_h17_h20() -> object:
    e = base_engine_mgc()
    _add_bo(e, 17, 0, 18, 0)
    _add_bo(e, 20, 0, 21, 0)
    return e


def main() -> None:
    print(f"{'='*120}")
    print("06 — combine best BO + risk variants")

    print("\n--- MNQ h08-09 BO + MGC default; risk variants")
    for sm, sg in [(1.00, 1.00), (1.00, 0.95), (1.00, 0.90), (0.95, 1.00), (0.95, 0.95),
                   (0.95, 0.90), (0.90, 1.00), (0.90, 0.95), (0.85, 1.00), (0.90, 0.85)]:
        bench(f"MNQ-h08 m={sm:.2f}/g={sg:.2f}",
              mnq_engine=mnq_h08(), mnq_risk=MNQ_BASE_RISK * sm,
              mgc_risk=MGC_BASE_RISK * sg)

    print("\n--- MNQ h08+h12 BO + MGC default; risk variants")
    for sm, sg in [(1.00, 1.00), (1.05, 1.00), (1.10, 1.00), (1.00, 1.05), (1.05, 1.05),
                   (1.10, 1.05), (1.10, 1.10)]:
        bench(f"MNQ-h08-h12 m={sm:.2f}/g={sg:.2f}",
              mnq_engine=mnq_h08_h12(), mnq_risk=MNQ_BASE_RISK * sm,
              mgc_risk=MGC_BASE_RISK * sg)

    print("\n--- MNQ h08+h13 BO + MGC default; risk variants")
    for sm, sg in [(1.00, 1.00), (1.05, 1.00), (1.05, 1.05), (1.10, 1.05)]:
        bench(f"MNQ-h08-h13 m={sm:.2f}/g={sg:.2f}",
              mnq_engine=mnq_h08_h13(), mnq_risk=MNQ_BASE_RISK * sm,
              mgc_risk=MGC_BASE_RISK * sg)

    print("\n--- MNQ h08 + MGC h17 BO combos")
    for sm, sg in [(1.00, 1.00), (1.00, 1.05), (1.05, 1.00), (1.05, 1.05), (1.10, 1.05)]:
        bench(f"MNQ-h08 + MGC-h17 m={sm:.2f}/g={sg:.2f}",
              mnq_engine=mnq_h08(), mgc_engine=mgc_h17(),
              mnq_risk=MNQ_BASE_RISK * sm, mgc_risk=MGC_BASE_RISK * sg)

    print("\n--- MNQ h08+h12 + MGC h17 combos")
    for sm, sg in [(1.00, 1.00), (1.05, 1.05), (1.10, 1.05), (1.10, 1.10), (1.15, 1.10)]:
        bench(f"MNQ-h08-h12 + MGC-h17 m={sm:.2f}/g={sg:.2f}",
              mnq_engine=mnq_h08_h12(), mgc_engine=mgc_h17(),
              mnq_risk=MNQ_BASE_RISK * sm, mgc_risk=MGC_BASE_RISK * sg)


if __name__ == "__main__":
    main()
