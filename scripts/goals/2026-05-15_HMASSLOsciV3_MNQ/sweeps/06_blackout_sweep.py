"""Step 6 — Block toxic hours discovered in step 5 (08-10 Brussels)."""
from _campaign import bench_v3, BEST_PARAMS, STRATEGY, make_engine_settings


def eng_with(extras=(), *, loss=1000.0, win=None):
    return make_engine_settings(
        STRATEGY,
        daily_loss_limit=loss, daily_win_limit=win,
        extra_active_windows=list(extras),
    )


def main() -> None:
    print("== Step 6a: Hour-block variations on top of BEST + loss_lim=$1000 ==")
    bench_v3("baseline (no extra blackout)", interval="3m",
             strategy_params=BEST_PARAMS, engine_settings=eng_with())

    variants = [
        ("Block 08-11",        [{"start_hour":8,"start_minute":0,"end_hour":11,"end_minute":0}]),
        ("Block 08-10",        [{"start_hour":8,"start_minute":0,"end_hour":10,"end_minute":0}]),
        ("Block 08-09",        [{"start_hour":8,"start_minute":0,"end_hour":9,"end_minute":0}]),
        ("Block 09-11",        [{"start_hour":9,"start_minute":0,"end_hour":11,"end_minute":0}]),
        ("Block 08-11 + 04",   [
            {"start_hour":4,"start_minute":0,"end_hour":5,"end_minute":0},
            {"start_hour":8,"start_minute":0,"end_hour":11,"end_minute":0},
        ]),
    ]
    for label, ex in variants:
        bench_v3(label, interval="3m", strategy_params=BEST_PARAMS,
                 engine_settings=eng_with(ex))


if __name__ == "__main__":
    main()
