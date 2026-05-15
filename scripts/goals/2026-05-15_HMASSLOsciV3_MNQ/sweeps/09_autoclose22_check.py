"""Sanity check: does the v3 winner still pass with auto_close=22 (CME close)?

Uses the EXACT 5 active blackouts of the winner preset (matches winner_preset.json).
"""
from _campaign import bench_v3, BEST_PARAMS, STRATEGY, make_engine_settings


# All 5 active blackouts as stored in winner_preset.json
ALL_ACTIVE_BLACKOUTS = [
    {"start_hour": 4,  "start_minute": 0,  "end_hour": 5,  "end_minute": 0},
    {"start_hour": 8,  "start_minute": 0,  "end_hour": 11, "end_minute": 0},
    {"start_hour": 11, "start_minute": 0,  "end_hour": 13, "end_minute": 0},
    {"start_hour": 15, "start_minute": 30, "end_hour": 21, "end_minute": 0},
    {"start_hour": 21, "start_minute": 0,  "end_hour": 23, "end_minute": 0},
]


def main() -> None:
    print("== auto_close=21 vs 22 — full 5-blackout set ==")
    for ac in [21, 22]:
        eng = make_engine_settings(
            STRATEGY,
            auto_close_hour=ac,
            daily_loss_limit=600.0, daily_win_limit=600.0,
            extra_active_windows=ALL_ACTIVE_BLACKOUTS,
        )
        bench_v3(f"auto_close={ac}h", interval="3m",
                 strategy_params=BEST_PARAMS, risk_per_trade=0.006,
                 engine_settings=eng)


if __name__ == "__main__":
    main()
