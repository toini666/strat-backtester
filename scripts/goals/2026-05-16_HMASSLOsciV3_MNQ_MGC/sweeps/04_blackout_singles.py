"""04 — single-hour blackout activation per leg (at baseline risk)."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _campaign import (  # noqa: E402
    DD_BUDGET, PNL_TARGET, base_engine_mgc, base_engine_mnq, bench,
)
from backend.api import BlackoutWindowSettings


def _add_blackout(es, sh, sm, eh, em):
    es.blackout_windows.append(BlackoutWindowSettings(
        active=True, start_hour=sh, start_minute=sm, end_hour=eh, end_minute=em))
    return es


def main() -> None:
    print(f"{'='*120}")
    print("04 — single-hour blackouts per leg @ baseline risk\n")

    # Baseline ref
    print("--- ref baseline (preset blackouts only)")
    bench("baseline")

    print("\n--- MNQ single-hour BO additions")
    for h_start, h_end in [(4, 5), (8, 9), (12, 13), (13, 14)]:
        em = _add_blackout(base_engine_mnq(), h_start, 0, h_end, 0)
        bench(f"MNQ BO h{h_start:02d}-{h_end:02d}", mnq_engine=em)

    print("\n--- MGC single-hour BO additions")
    for h_start, h_end in [(8, 9), (17, 18), (20, 21), (21, 22)]:
        em = _add_blackout(base_engine_mgc(), h_start, 0, h_end, 0)
        bench(f"MGC BO h{h_start:02d}-{h_end:02d}", mgc_engine=em)

    print("\n--- MNQ pair combos (good single + good single)")
    for hs in [(4, 5), (8, 9), (12, 13)]:
        e = _add_blackout(base_engine_mnq(), 8, 0, 9, 0)
        e = _add_blackout(e, *hs, *([hs[1] if False else None]) if False else (hs[0]+1, hs[1])) if False else e
        # simpler — combine 8-9 with each other
        e = base_engine_mnq()
        _add_blackout(e, 8, 0, 9, 0)
        _add_blackout(e, hs[0], 0, hs[1], 0)
        if hs == (8, 9):
            continue
        bench(f"MNQ BO h08+h{hs[0]:02d}", mnq_engine=e)

    print("\n--- MGC pair combos")
    for hs in [(17, 18), (20, 21), (21, 22), (8, 9)]:
        e = base_engine_mgc()
        _add_blackout(e, 17, 0, 18, 0)
        if hs == (17, 18):
            continue
        _add_blackout(e, hs[0], 0, hs[1], 0)
        bench(f"MGC BO h17+h{hs[0]:02d}", mgc_engine=e)


if __name__ == "__main__":
    main()
