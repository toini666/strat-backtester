"""Step 8 — Final validation of the winning config + 3 closest alternatives."""
from _campaign import bench_v3, BEST_PARAMS, STRATEGY, make_engine_settings


EXTRAS = [
    {"start_hour": 4, "start_minute": 0, "end_hour": 5, "end_minute": 0},
    {"start_hour": 8, "start_minute": 0, "end_hour": 11, "end_minute": 0},
]


def main() -> None:
    print("== Step 8: FINAL VALIDATION ==")

    # WINNER: r=0.6%, W=600/L=600, extra blackouts 04 + 08-11
    bench_v3(
        "WINNER",
        interval="3m",
        strategy_params=BEST_PARAMS,
        risk_per_trade=0.006,
        engine_settings=make_engine_settings(
            STRATEGY, daily_loss_limit=600.0, daily_win_limit=600.0,
            extra_active_windows=EXTRAS,
        ),
    )
    # ALT1: simpler — no win cap
    bench_v3(
        "ALT1: L=600 only",
        interval="3m", strategy_params=BEST_PARAMS, risk_per_trade=0.006,
        engine_settings=make_engine_settings(
            STRATEGY, daily_loss_limit=600.0, extra_active_windows=EXTRAS,
        ),
    )
    # ALT2: tighter risk / tighter caps
    bench_v3(
        "ALT2: r=0.5% W=500 L=500",
        interval="3m", strategy_params=BEST_PARAMS, risk_per_trade=0.005,
        engine_settings=make_engine_settings(
            STRATEGY, daily_loss_limit=500.0, daily_win_limit=500.0,
            extra_active_windows=EXTRAS,
        ),
    )
    # ALT3: no daily limits, low risk
    bench_v3(
        "ALT3: r=0.4% no limits",
        interval="3m", strategy_params=BEST_PARAMS, risk_per_trade=0.004,
        engine_settings=make_engine_settings(STRATEGY, extra_active_windows=EXTRAS),
    )


if __name__ == "__main__":
    main()
