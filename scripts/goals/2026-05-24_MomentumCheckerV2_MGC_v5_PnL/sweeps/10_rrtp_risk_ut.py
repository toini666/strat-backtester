"""Phase 10 - rr_tp + risk_per_trade + ut_on recheck at new BO anchor.

Math anchor (advisor): with edge ~6.6 pp on this anchor, soft WR floor 51.5%.
  rr_tp=1.25 -> BE_WR=44.4 %, current 52.5 %
  rr_tp=1.30 -> BE_WR=43.5 %, expect ~50.1 % (at floor)
  rr_tp=1.35 -> BE_WR=42.6 %, expect ~49.2 % (BELOW)
So cap rr_tp <= 1.30 strictly. Also probe 1.20 / 1.22 (slightly higher WR).
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.goals._shared.harness import bench  # noqa: E402
from _anchor import anchor_kwargs  # noqa: E402


def main() -> None:
    print("Phase 10 - rr_tp x risk + ut recheck")
    print("=" * 80)
    bench("anchor (rr=1.25 ut_off risk=0.42%)", **anchor_kwargs())

    print("\n--- rr_tp sweep (risk fixed at 0.42 %) ---")
    for rr in [1.15, 1.20, 1.22, 1.25, 1.28, 1.30]:
        bench(f"rr_tp={rr}", **anchor_kwargs(params_override={"rr_tp": rr}))

    print("\n--- ut_on=True recheck (rr=1.25) ---")
    for ut_key in [1.4, 1.5, 1.6, 1.8, 2.0]:
        for ut_atr in [7, 10, 14]:
            bench(f"ut_on key={ut_key} atr={ut_atr}",
                  **anchor_kwargs(params_override={"ut_on": True, "ut_key": ut_key, "ut_atr_period": ut_atr}))

    print("\n--- risk_per_trade sweep (fine grid, current 0.42%) ---")
    for risk_pct in [0.37, 0.38, 0.39, 0.40, 0.41, 0.42, 0.43, 0.44, 0.45, 0.46, 0.47, 0.48, 0.50]:
        bench(f"risk={risk_pct:.2f}%", **anchor_kwargs(risk=risk_pct / 100.0))


if __name__ == "__main__":
    main()
