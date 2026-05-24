"""Phase 4 — EMA prin/sec × SL combo (the highest-EV bet).

MGC v2 found `ema_prin=15 ema_sec=7` gives +$5,679 PnL but +$636 DD over budget.
This phase combines `ema_prin=15` with EVERY DD-reducing lever, hoping to
unlock that PnL gain while keeping DD ≤ $2,135.

Sub-phases:
- 4a: ema_prin 1D
- 4b: ema_sec 1D
- 4c: ema_prin × ema_sec joint grid
- 4d: KEY — ema_prin=15 × sl_max_points (low values can shrink the DD)
- 4e: ema_prin=15 × tick_buffer
- 4f: ema_prin=15 × be_at_rr (BE earlier might cushion DD)
- 4g: ema_prin=15 × max_candle_pct
- 4h: ema_prin=15 × sl_min_pct (revisit — anchor has changed)
"""
from __future__ import annotations

import sys
from pathlib import Path

CAMPAIGN = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CAMPAIGN / "sweeps"))

from _helper import bench  # type: ignore


def header(title: str) -> None:
    print("\n" + "=" * 78)
    print(f"  {title}")
    print("=" * 78)


def main() -> None:
    header("Phase 4a — ema_prin_len 1D (seed=30)")
    for v in [9, 12, 15, 18, 21, 25, 30, 35, 40, 50]:
        bench(f"ema_prin={v}", params={"ema_prin_len": v})

    header("Phase 4b — ema_sec_len 1D (seed=5)")
    for v in [3, 5, 7, 9, 13, 18, 21, 30]:
        bench(f"ema_sec={v}", params={"ema_sec_len": v})

    header("Phase 4c — ema_prin × ema_sec joint grid")
    for p in [12, 15, 18, 21, 25, 30]:
        for s in [3, 5, 7, 9, 13]:
            bench(f"prin={p:>2} sec={s:>2}", params={"ema_prin_len": p, "ema_sec_len": s})

    header("Phase 4d — ema_prin=15 × sl_max_points (look for DD reduction)")
    for s in [3, 5, 7, 9]:
        for smax in [40, 50, 60, 70, 80, 100, 120]:
            bench(
                f"prin=15 sec={s} sl_max={smax}",
                params={"ema_prin_len": 15, "ema_sec_len": s, "sl_max_points": float(smax)},
            )

    header("Phase 4e — ema_prin=15 sec=7 × tick_buffer")
    for tb in [0, 1, 2, 3, 4, 5]:
        bench(
            f"prin=15 sec=7 tb={tb}",
            params={"ema_prin_len": 15, "ema_sec_len": 7, "tick_buffer": tb},
        )

    header("Phase 4f — ema_prin=15 sec=7 × be_at_rr")
    for be in [0.0, 1.0, 1.5, 2.0, 2.5, 3.0]:
        bench(
            f"prin=15 sec=7 be={be}",
            params={"ema_prin_len": 15, "ema_sec_len": 7, "be_at_rr": be},
        )

    header("Phase 4g — ema_prin=15 sec=7 × max_candle_pct")
    for mcp in [0.18, 0.20, 0.22, 0.25, 0.28]:
        bench(
            f"prin=15 sec=7 mcp={mcp}",
            params={"ema_prin_len": 15, "ema_sec_len": 7, "max_candle_pct": mcp},
        )

    header("Phase 4h — ema_prin=15 sec=7 × sl_min_pct (NEW lever revisit)")
    for mp in [0.0, 0.05, 0.10, 0.15, 0.20]:
        bench(
            f"prin=15 sec=7 sl_min_pct={mp}",
            params={"ema_prin_len": 15, "ema_sec_len": 7, "sl_min_pct": mp},
        )


if __name__ == "__main__":
    main()
