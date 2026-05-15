"""Step 7 — Fine tune risk / daily-limit ratio on final config."""
from _campaign import bench_v3, BEST_PARAMS, STRATEGY, make_engine_settings


EXTRAS = [
    {"start_hour": 4, "start_minute": 0, "end_hour": 5, "end_minute": 0},
    {"start_hour": 8, "start_minute": 0, "end_hour": 11, "end_minute": 0},
]


def eng(*, loss, win=None, mode="after_close"):
    return make_engine_settings(
        STRATEGY,
        daily_loss_limit=loss, daily_win_limit=win,
        extra_active_windows=EXTRAS,
        daily_limit_mode=mode,
    )


def main() -> None:
    print("== Step 7: Final tuning around the winning zone ==")
    cfgs = [
        # (risk, loss_lim, win_lim, label)
        (0.006, 500, None, "r=0.6% L=500"),
        (0.006, 600, None, "r=0.6% L=600"),
        (0.006, 700, 700, "r=0.6% W=700 L=700"),
        (0.006, 600, 600, "r=0.6% W=600 L=600"),  # ← WINNER
        (0.005, 500, 500, "r=0.5% W=500 L=500"),
        (0.0065, 600, 800, "r=0.65% W=800 L=600"),
        (0.007, 700, None, "r=0.7% L=700"),
    ]
    for r, ll, wl, label in cfgs:
        bench_v3(label, interval="3m", strategy_params=BEST_PARAMS,
                 risk_per_trade=r, engine_settings=eng(loss=ll, win=wl))


if __name__ == "__main__":
    main()
