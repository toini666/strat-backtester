"""Step 3 — Oscillator core params on M3 + cloud_on base."""
from _campaign import bench_v3


BASE = {"cloud_on": True, "one_trade_per_entry_window": False}


def main() -> None:
    print("== Step 3: Oscillator core params on M3 +cloud +one_trade=F ==")
    bench_v3("BASE", interval="3m", strategy_params=BASE)
    for v in [3, 4, 5, 6, 7]:
        bench_v3(f"hyper_wave_length={v}", interval="3m",
                 strategy_params={**BASE, "hyper_wave_length": v})
    for v in [2, 3, 4, 5]:
        bench_v3(f"signal_length={v}", interval="3m",
                 strategy_params={**BASE, "signal_length": v})
    for v in [15.0, 20.0, 25.0, 30.0, 35.0, 40.0, 50.0]:
        bench_v3(f"sig_extreme={v}", interval="3m",
                 strategy_params={**BASE, "sig_extreme": v})
    for v in [25, 35, 45, 55]:
        bench_v3(f"mf_length={v}", interval="3m",
                 strategy_params={**BASE, "mf_length": v})
    for v in [3, 4, 5, 6, 8, 10]:
        bench_v3(f"entry_window_bars={v}", interval="3m",
                 strategy_params={**BASE, "entry_window_bars": v})


if __name__ == "__main__":
    main()
