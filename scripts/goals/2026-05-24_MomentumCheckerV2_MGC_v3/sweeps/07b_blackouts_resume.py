"""Phase 7 resume — re-run 7b onwards after fixing tuple bug."""
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


def header(t):
    print("\n" + "=" * 78)
    print(f"  {t}")
    print("=" * 78)


def main():
    header("Phase 7b — Add early-morning ref blackout")
    for sh, sm, eh, em in [(0,0,0,30), (0,0,0,59), (0,0,1,0), (0,0,1,30), (0,0,2,0), (0,30,1,30)]:
        bench(f"+{sh:02d}:{sm:02d}-{eh:02d}:{em:02d}",
              engine_settings=es_with(*SEED_WINDOWS, (sh, sm, eh, em)))

    header("Phase 7c — Extend lunch blackout")
    bench("12:00-14:00 (extend lunch)",
          engine_settings=es_with(*[w for w in SEED_WINDOWS if w != (12,30,14,0)] + [(12,0,14,0)]))
    bench("12:00-14:30",
          engine_settings=es_with(*[w for w in SEED_WINDOWS if w != (12,30,14,0)] + [(12,0,14,30)]))

    header("Phase 7d — Trim afternoon windows")
    bench("REMOVE 15:30-17",
          engine_settings=es_with(*[w for w in SEED_WINDOWS if w != (15,30,17,0)]))
    bench("REMOVE 18-19",
          engine_settings=es_with(*[w for w in SEED_WINDOWS if w != (18,0,19,0)]))
    bench("REMOVE 20-21",
          engine_settings=es_with(*[w for w in SEED_WINDOWS if w != (20,0,21,0)]))
    bench("15:00-17 (widen)",
          engine_settings=es_with(*[w for w in SEED_WINDOWS if w != (15,30,17,0)] + [(15,0,17,0)]))
    bench("17:00-18 (replace 18-19)",
          engine_settings=es_with(*[w for w in SEED_WINDOWS if w != (18,0,19,0)] + [(17,0,18,0)]))

    header("Phase 7e — +07-08 (MNQ v4 found this helped)")
    bench("+07:00-08:00", engine_settings=es_with(*SEED_WINDOWS, (7, 0, 8, 0)))
    bench("+06:30-07:30", engine_settings=es_with(*SEED_WINDOWS, (6, 30, 7, 30)))

    header("Phase 7f — +H=09/H=10 (weak hours)")
    bench("+09:00-10:00", engine_settings=es_with(*SEED_WINDOWS, (9, 0, 10, 0)))
    bench("+10:00-11:00", engine_settings=es_with(*SEED_WINDOWS, (10, 0, 11, 0)))
    bench("+09:00-11:00", engine_settings=es_with(*SEED_WINDOWS, (9, 0, 11, 0)))

    header("Phase 7g — +01-02 (H=01 border, 32% WR)")
    bench("+01:00-02:00", engine_settings=es_with(*SEED_WINDOWS, (1, 0, 2, 0)))
    bench("+00:00-02:00", engine_settings=es_with(*SEED_WINDOWS, (0, 0, 2, 0)))

    header("Phase 7h — Combos with promising single additions (preview)")
    # Combine 21:30-23:59 + +0-1 (catches DST H=23)
    bench("21:30-23:59 + 0-1",
          engine_settings=es_with(*[w for w in SEED_WINDOWS if w != (22,0,23,59)] + [(21,30,23,59), (0,0,1,0)]))
    bench("seed + 0-1 + 07-08",
          engine_settings=es_with(*SEED_WINDOWS, (0,0,1,0), (7,0,8,0)))


if __name__ == "__main__":
    main()
