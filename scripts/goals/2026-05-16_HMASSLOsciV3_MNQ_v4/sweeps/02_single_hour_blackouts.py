"""02 — Single-hour blackouts on v3 winner base.

Per hour analysis from sweep 01, toxic hours are:
  H=11 (-$2,086), H=12 (-$1,926), H=08 (-$1,447), H=14 (-$1,242), H=06 (-$971)

We test each one individually as a 1-hour blackout window. Plus a few
neighbors and the diagnostic hours from v3 REPORT to compare.

Sim count: ~15.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _campaign as C  # noqa: E402

from scripts.goals._shared.harness import bench  # noqa: E402
from scripts.goals._shared.engine_settings import make_engine_settings  # noqa: E402


def _window_dict(start_h, end_h):
    # Cap end at 23:59 because BlackoutWindowSettings validates end_hour ≤ 23.
    if end_h >= 24:
        return {"start_hour": start_h, "start_minute": 0, "end_hour": 23, "end_minute": 59}
    return {"start_hour": start_h, "start_minute": 0, "end_hour": end_h, "end_minute": 0}


def run_with_blackout(label, windows, risk=C.DEFAULT_RISK):
    es = make_engine_settings(
        C.STRATEGY,
        extra_active_windows=[_window_dict(w[0], w[1]) for w in windows],
    )
    return bench(
        f"{label:<55s} r={risk:.4f}",
        strategy_name=C.STRATEGY, symbol=C.SYMBOL, interval=C.TF,
        start=C.START, end=C.END,
        strategy_params=dict(C.V3_WINNER_PARAMS),
        initial_equity=C.INITIAL_EQUITY,
        risk_per_trade=risk,
        max_contracts=C.MAX_CONTRACTS,
        engine_settings=es,
    )


def main():
    print(f"=== 02 SINGLE-HOUR BLACKOUTS — TF={C.TF} ===\n")
    print("Base = v3 winner (cd=3, sx=40, hw_dir_on=False), r=0.0032")
    print("Adds ONE 1-hour blackout window (start_h → start_h+1)\n")

    rows = []

    # Toxic hours from sweep 01 (most negative first)
    # Skip already-tested in baseline retry.
    for h in [23, 0]:
        rows.append((f"H={h:02d}", run_with_blackout(f"BO h={h:02d}-{h+1:02d}", [(h, h + 1)])))

    print("\n=== TOP 12 by PnL/DD ratio ===")
    def sortkey(row):
        s = row[1]
        passes = s["max_dd_$"] < C.TARGET_MAX_DD and s["net_pnl"] >= C.TARGET_PNL_MIN
        return (-int(passes), -(s["net_pnl"] / max(s["max_dd_$"], 1.0)))
    rows.sort(key=sortkey)
    for label, s in rows[:12]:
        ratio = s["net_pnl"] / max(s["max_dd_$"], 1.0)
        mark = "✓" if s["max_dd_$"] < C.TARGET_MAX_DD and s["net_pnl"] >= C.TARGET_PNL_MIN else " "
        print(f"  {mark} {label:<25s}  ratio={ratio:>6.2f}  "
              f"PnL=${s['net_pnl']:>9,.0f}  DD=${s['max_dd_$']:>6,.0f}  "
              f"PF={s['profit_factor']}  N={s['trades']}")


if __name__ == "__main__":
    main()
