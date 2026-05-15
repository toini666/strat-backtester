"""Step 4 — Daily win/loss limits + risk scaling on tuned base."""
from _campaign import bench_v3, BEST_PARAMS, make_engine_settings, STRATEGY


def eng(loss=None, win=None):
    return make_engine_settings(STRATEGY, daily_loss_limit=loss, daily_win_limit=win)


def main() -> None:
    print("== Step 4a: Risk reduction at 1% baseline ==")
    for r in [0.01, 0.005, 0.003, 0.002]:
        bench_v3(f"r={r:.3f} no limits", interval="3m",
                 strategy_params=BEST_PARAMS, risk_per_trade=r)

    print("\n== Step 4b: Daily loss limit (after_close) ==")
    for loss in [300, 500, 700, 1000, 1500]:
        bench_v3(f"Loss limit ${loss}", interval="3m",
                 strategy_params=BEST_PARAMS, risk_per_trade=0.01,
                 engine_settings=eng(loss=float(loss)))

    print("\n== Step 4c: Win + Loss daily caps ==")
    for w, l in [(500, 500), (700, 500), (1000, 700), (1500, 1000)]:
        bench_v3(f"Win=${w} Loss=${l}", interval="3m",
                 strategy_params=BEST_PARAMS, risk_per_trade=0.01,
                 engine_settings=eng(win=float(w), loss=float(l)))


if __name__ == "__main__":
    main()
