"""06 — Add toxic-hour blackouts incrementally based on 05's hour buckets.

Hours flagged by sweep 05 (negative or near-zero PnL per hour) are added one by
one as 1h ACTIVE blackouts. We track cumulative PnL/DD/PF to validate the
additive effect and stop adding when no further lift.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _campaign as C  # noqa: E402

from scripts.goals._shared.engine_settings import make_engine_settings  # noqa: E402
from scripts.goals._shared.harness import bench  # noqa: E402

TF = "7m"
BASE_PARAMS = {
    "hw_range_on": True,
    "hma2_len": 34,
}
RISK = 0.01

# Toxic hours from 05_hour_analysis.json — ranked by absolute loss.
# Each entry = (start_hour, start_minute, end_hour, end_minute, reason).
BLACKOUT_CANDIDATES = [
    (11, 0, 12, 0, "H=11 -$8,125 (32% WR, 80 trades) — UK lunch handoff"),
    (8, 0, 9, 0, "H=08 -$6,188 (38% WR, 64 trades) — UK pre-open"),
    (3, 0, 4, 0, "H=03 -$5,362 (40% WR, 77 trades) — Asia mid-session"),
    (17, 0, 18, 0, "H=17 -$3,842 (43% WR, 69 trades) — US mid-afternoon"),
    (23, 0, 0, 0, "H=23 -$2,390 (20% WR, 10 trades) — pre-rollover"),
]


def with_blackouts(active_windows):
    return make_engine_settings(
        C.STRATEGY,
        extra_active_windows=[{"start_hour": sh, "start_minute": sm,
                               "end_hour": eh, "end_minute": em}
                              for (sh, sm, eh, em, _) in active_windows],
    )


def main():
    print(f"=== 06 BLACKOUT sweep — M7 {BASE_PARAMS} risk={RISK} ===\n", flush=True)
    rows = []

    # 1) base (no extra blackouts)
    s = bench(
        label="base (no extra blackouts)",
        strategy_name=C.STRATEGY, symbol=C.SYMBOL,
        interval=TF, start=C.START, end=C.END,
        strategy_params=BASE_PARAMS,
        initial_equity=C.INITIAL_EQUITY,
        risk_per_trade=RISK,
        max_contracts=C.MAX_CONTRACTS,
    )
    s["windows"] = []
    rows.append(s)

    # 2) incremental: add one window at a time, accumulate
    accumulated = []
    for window in BLACKOUT_CANDIDATES:
        accumulated.append(window)
        es = with_blackouts(accumulated)
        label = " + ".join(f"{w[0]:02d}-{w[2]:02d}h" for w in accumulated)
        s = bench(
            label=label,
            strategy_name=C.STRATEGY, symbol=C.SYMBOL,
            interval=TF, start=C.START, end=C.END,
            strategy_params=BASE_PARAMS,
            initial_equity=C.INITIAL_EQUITY,
            risk_per_trade=RISK,
            max_contracts=C.MAX_CONTRACTS,
            engine_settings=es,
        )
        s["windows"] = list(accumulated)
        s["ratio_p_dd"] = round(s["net_pnl"] / s["max_dd_$"], 2) if s["max_dd_$"] > 0 else None
        rows.append(s)

    out = Path(__file__).resolve().parents[1] / "logs" / "06_blackout_sweep.json"
    out.write_text(json.dumps(rows, indent=2, default=str))
    print(f"\n[saved] {out}")


if __name__ == "__main__":
    main()
