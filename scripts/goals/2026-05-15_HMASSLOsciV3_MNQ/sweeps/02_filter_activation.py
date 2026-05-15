"""Step 2 — Toggle MFI/cloud/range/delta filters on M3."""
from _campaign import bench_v3


def main() -> None:
    print("== Step 2: Filter activation on M3 ==")
    bench_v3("M3 defaults", interval="3m")
    bench_v3("M3 +cloud_on", interval="3m", strategy_params={"cloud_on": True})
    bench_v3("M3 +cloud_zero_on", interval="3m", strategy_params={"cloud_zero_on": True})
    bench_v3("M3 +hw_range_on", interval="3m", strategy_params={"hw_range_on": True})
    bench_v3("M3 +delta_ext_on", interval="3m", strategy_params={"delta_ext_on": True})
    bench_v3("M3 +cloud+hw_range", interval="3m",
             strategy_params={"cloud_on": True, "hw_range_on": True})
    bench_v3("M3 +cloud+delta_ext", interval="3m",
             strategy_params={"cloud_on": True, "delta_ext_on": True})
    bench_v3("M3 ALL filters on", interval="3m",
             strategy_params={"cloud_on": True, "cloud_zero_on": True,
                              "hw_range_on": True, "delta_ext_on": True})


if __name__ == "__main__":
    main()
