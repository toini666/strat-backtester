"""Step 1 — Baseline per timeframe with strategy defaults."""
from _campaign import bench_v3


def main() -> None:
    print("== Step 1: Baseline default params per TF ==")
    for tf in ["3m", "5m", "7m", "10m"]:
        bench_v3(f"TF={tf} defaults", interval=tf)


if __name__ == "__main__":
    main()
