"""08 — precision finetune around triple BO h08+h12+h13 (P/DD=42)."""
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


def mnq_h08_h12_h13() -> object:
    e = base_engine_mnq()
    _add(e, 8, 0, 9, 0); _add(e, 12, 0, 13, 0); _add(e, 13, 0, 14, 0); return e


def mnq_h08_h12_h13_h04() -> object:
    e = mnq_h08_h12_h13(); _add(e, 4, 0, 5, 0); return e


def mnq_h08_h12_h13_widerH11() -> object:
    """h08, h12, h13, AND extend h11 → 12 to 11-14 (currently 11-12 + 14-15 active)."""
    e = mnq_h08_h12_h13(); _add(e, 14, 0, 15, 0)  # already on but harmless duplicate
    return e


def main() -> None:
    print(f"{'='*120}")
    print("08 — precision finetune triple BO h08+h12+h13\n")

    print("--- A. Fine risk grid m∈[1.00..1.08] × g∈[1.05..1.12]")
    for sm_pct in (100, 101, 102, 103, 104, 105, 106, 107, 108):
        for sg_pct in (105, 107, 108, 109, 110, 112):
            sm = sm_pct / 100
            sg = sg_pct / 100
            bench(f"3BO m={sm:.2f}/g={sg:.2f}",
                  mnq_engine=mnq_h08_h12_h13(), mnq_risk=MNQ_BASE_RISK * sm,
                  mgc_risk=MGC_BASE_RISK * sg)

    print("\n--- B. 3BO + MNQ h04 (quad) finetune")
    for sm_pct in (100, 105, 110, 115):
        for sg_pct in (105, 110, 115):
            sm = sm_pct / 100
            sg = sg_pct / 100
            bench(f"4BO m={sm:.2f}/g={sg:.2f}",
                  mnq_engine=mnq_h08_h12_h13_h04(), mnq_risk=MNQ_BASE_RISK * sm,
                  mgc_risk=MGC_BASE_RISK * sg)


if __name__ == "__main__":
    main()
