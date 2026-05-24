"""Phase 8 — Combo lattice on the survivors from Phases 1-7.

Survivors discovered:
- ema_prin=15 sec=7 or sec=9 (highest WR @ +$321 DD)
- ema_prin=18 sec=7 (highest PnL @ +$321 DD)
- sl_max=120 (free +$453 PnL same DD on seed anchor)
- Blackouts: TBD from Phase 7

DD-reducer lever: TBD (blackouts most likely)

The combo grid tests every viable (ema_prin × sl_max × blackout-set × risk_per_trade)
combination to find the highest PnL strictly under DD ≤ $2,135.
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


def es_with(*windows):
    bw = [
        BlackoutWindowSettings(
            active=True, start_hour=sh, start_minute=sm, end_hour=eh, end_minute=em
        )
        for (sh, sm, eh, em) in windows
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


SEED_WINDOWS = list(SEED_BLACKOUTS_ACTIVE)


def header(title: str) -> None:
    print("\n" + "=" * 78)
    print(f"  {title}")
    print("=" * 78)


# These will be set after Phase 7 completes — manually edit before running:
BEST_BLACKOUT_SET = SEED_WINDOWS  # placeholder; replace with Phase 7 winner


def main() -> None:
    header("Phase 8a — ema_prin × ema_sec × sl_max=120 × blackout-set")
    for prin in [15, 18]:
        for sec in [5, 7, 9]:
            bench(
                f"prin={prin} sec={sec} sl_max=120 BO_seed",
                params={"ema_prin_len": prin, "ema_sec_len": sec, "sl_max_points": 120.0},
                engine_settings=es_with(*SEED_WINDOWS),
            )

    header("Phase 8b — Best EMA × Best blackout set × risk variations")
    # Filled after Phase 7 identifies the best blackout set
    # for prin in [15, 18]:
    #     for sec in [7, 9]:
    #         for risk_pct in [0.0048, 0.0050, 0.0053]:
    #             bench(f"prin={prin} sec={sec} risk={risk_pct*100:.2f}",
    #                   params={"ema_prin_len": prin, "ema_sec_len": sec, "sl_max_points": 120.0},
    #                   engine_settings=es_with(*BEST_BLACKOUT_SET),
    #                   risk_per_trade=risk_pct)


if __name__ == "__main__":
    main()
