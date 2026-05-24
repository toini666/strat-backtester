"""Phase 9 — Fine risk-band crawl around the combo winner.

Run after Phase 8 has identified the best param + blackout combo.
Crawl risk_per_trade in 5-basis-point steps to find the max-PnL cell
respecting the DD budget.

Adjust WINNER_BASE_OVERRIDES, WINNER_BLACKOUT_PATCH below to match Phase 8.
"""
from __future__ import annotations

import sys
from pathlib import Path

CAMPAIGN = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CAMPAIGN / "sweeps"))

from _helper import bench  # type: ignore
from backend.api import BacktestEngineSettings, BlackoutWindowSettings  # noqa: E402
from sweeps._campaign import (  # type: ignore
    SEED_AUTO_CLOSE_H,
    SEED_AUTO_CLOSE_M,
    SEED_BLACKOUTS_ACTIVE,
)


WINNER_BASE_OVERRIDES: dict = {
    # filled in after Phase 8
}

# (Use seed blackouts unless Phase 7 finds a better set; will be patched.)
WINNER_BLACKOUTS = list(SEED_BLACKOUTS_ACTIVE)


def es():
    bw = [
        BlackoutWindowSettings(
            active=True, start_hour=sh, start_minute=sm, end_hour=eh, end_minute=em
        )
        for (sh, sm, eh, em) in WINNER_BLACKOUTS
    ]
    return BacktestEngineSettings(
        auto_close_enabled=True,
        auto_close_hour=SEED_AUTO_CLOSE_H,
        auto_close_minute=SEED_AUTO_CLOSE_M,
        blackout_windows=bw,
        debug=False,
        daily_win_limit_enabled=False,
        daily_win_limit=500.0,
        daily_loss_limit_enabled=False,
        daily_loss_limit=700.0,
        daily_limit_mode="after_close",
    )


def header(title: str) -> None:
    print("\n" + "=" * 78)
    print(f"  {title}")
    print("=" * 78)


def main() -> None:
    header("Phase 9 — Fine risk crawl around the combo winner")
    for risk_pct in [0.0040, 0.0045, 0.0048, 0.0050, 0.0052, 0.0053,
                     0.0054, 0.0055, 0.0056, 0.0058, 0.0060, 0.0063]:
        bench(
            f"risk={risk_pct*100:.3f}%",
            params=WINNER_BASE_OVERRIDES,
            risk_per_trade=risk_pct,
            engine_settings=es(),
        )

    header("Phase 9b — 1-basis-point edge crawl (fill after coarse pass)")


if __name__ == "__main__":
    main()
