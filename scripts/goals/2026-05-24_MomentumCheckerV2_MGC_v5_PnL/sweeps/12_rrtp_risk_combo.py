"""Phase 12 - Combine rr_tp / ut_on / risk on the new anchor.

Single-lever wins (each vs L6+LO5+hma2=76 anchor PnL $45,434 / DD $1,934):
  rr_tp=1.22       -> $45,793 / DD $1,944  (+0.7pp WR margin)
  rr_tp=1.28       -> $45,582 / DD $1,925
  ut_on K=2.0 A=10 -> $46,007 / DD $2,040
  risk=0.50 %      -> $48,172 / DD $2,251
  risk=0.46 %      -> $46,482 / DD $2,086
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
    print("Phase 12 - rr_tp / ut_on / risk crystallize")
    print("=" * 80)
    bench("anchor (rr=1.25 ut_off risk=0.42%)", **anchor_kwargs())

    print("\n--- rr_tp=1.22 x risk sweep ---")
    for risk_pct in [0.42, 0.45, 0.46, 0.48, 0.50, 0.52, 0.55]:
        bench(f"rr=1.22 risk={risk_pct:.2f}%",
              **anchor_kwargs(params_override={"rr_tp": 1.22}, risk=risk_pct / 100.0))

    print("\n--- rr_tp=1.25 (current) x risk fine ---")
    for risk_pct in [0.50, 0.52, 0.55, 0.58, 0.60]:
        bench(f"rr=1.25 risk={risk_pct:.2f}%",
              **anchor_kwargs(risk=risk_pct / 100.0))

    print("\n--- rr_tp=1.28 x risk ---")
    for risk_pct in [0.45, 0.48, 0.50, 0.52]:
        bench(f"rr=1.28 risk={risk_pct:.2f}%",
              **anchor_kwargs(params_override={"rr_tp": 1.28}, risk=risk_pct / 100.0))

    print("\n--- ut_on K=2.0 A=10 x risk ---")
    for risk_pct in [0.42, 0.45, 0.46, 0.48]:
        bench(f"ut_on K=2.0 A=10 risk={risk_pct:.2f}%",
              **anchor_kwargs(params_override={"ut_on": True, "ut_key": 2.0, "ut_atr_period": 10},
                              risk=risk_pct / 100.0))

    print("\n--- rr=1.22 + ut_on K=2.0 A=10 x risk ---")
    for risk_pct in [0.42, 0.45, 0.48, 0.50]:
        bench(f"rr=1.22 ut_on K=2.0 A=10 risk={risk_pct:.2f}%",
              **anchor_kwargs(params_override={"rr_tp": 1.22, "ut_on": True, "ut_key": 2.0, "ut_atr_period": 10},
                              risk=risk_pct / 100.0))


if __name__ == "__main__":
    main()
