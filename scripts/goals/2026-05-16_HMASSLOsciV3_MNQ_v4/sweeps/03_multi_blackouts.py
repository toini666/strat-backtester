"""03 — Multi-hour blackout combos.

From sweep 02 (r=0.0032 fixed):
  BO h=11-12 → $37,945 / $2,467 (ratio 15.38)  -- best single by PnL
  BO h=14-15 → $36,269 / $2,324 (ratio 15.61)  -- best single by ratio
  BO h=08-09 → $35,423 / $2,382 (ratio 14.87)
  BO h=06-07 → $34,615 / $2,493 (marginal)
  BO h=21-22 → $34,362 / $2,407 (PnL too low)
  BO h=12-13 → $35,168 / $3,035 (DD WORSENED — non-trivial)
  BO h=20-21 → $35,207 / $2,739 (DD worsened)

We combine the orthogonal improvers (h=11-12 and h=14-15) and add cautious
neighbors. Risk fan at the end of the most promising combos.

Sim count: ~25
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _campaign as C  # noqa: E402

from scripts.goals._shared.harness import bench  # noqa: E402
from scripts.goals._shared.engine_settings import make_engine_settings  # noqa: E402


def _window_dict(start_h, end_h):
    if end_h >= 24:
        return {"start_hour": start_h, "start_minute": 0, "end_hour": 23, "end_minute": 59}
    return {"start_hour": start_h, "start_minute": 0, "end_hour": end_h, "end_minute": 0}


def run_with_blackouts(label, windows, risk=C.DEFAULT_RISK):
    es = make_engine_settings(
        C.STRATEGY,
        extra_active_windows=[_window_dict(s, e) for s, e in windows],
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
    print(f"=== 03 MULTI-HOUR BLACKOUTS — TF={C.TF} ===\n")
    print("Base = v3 winner. Combine top singles + neighbors.\n")

    rows = []

    # --- 2-hour combos (top pairs) ---
    print("--- 2-hour combos ---")
    rows.append(("BO 11+14", run_with_blackouts("BO 11+14", [(11, 12), (14, 15)])))
    rows.append(("BO 11+08", run_with_blackouts("BO 11+08", [(11, 12), (8, 9)])))
    rows.append(("BO 14+08", run_with_blackouts("BO 14+08", [(14, 15), (8, 9)])))
    rows.append(("BO 11+06", run_with_blackouts("BO 11+06", [(11, 12), (6, 7)])))
    rows.append(("BO 14+06", run_with_blackouts("BO 14+06", [(14, 15), (6, 7)])))
    rows.append(("BO 11+21", run_with_blackouts("BO 11+21", [(11, 12), (21, 22)])))
    rows.append(("BO 14+21", run_with_blackouts("BO 14+21", [(14, 15), (21, 22)])))

    # --- 3-hour combos ---
    print("\n--- 3-hour combos ---")
    rows.append(("BO 11+14+08", run_with_blackouts("BO 11+14+08",
                                                   [(11, 12), (14, 15), (8, 9)])))
    rows.append(("BO 11+14+06", run_with_blackouts("BO 11+14+06",
                                                   [(11, 12), (14, 15), (6, 7)])))
    rows.append(("BO 11+14+21", run_with_blackouts("BO 11+14+21",
                                                   [(11, 12), (14, 15), (21, 22)])))
    rows.append(("BO 11+14+08+06", run_with_blackouts("BO 11+14+08+06",
                                                      [(11, 12), (14, 15), (8, 9), (6, 7)])))

    # --- Risk fan on the top 2-hour and top 3-hour combos ---
    print("\n--- Risk fan: BO 11+14 ---")
    for r in [0.0030, 0.0032, 0.0034, 0.0036, 0.0038, 0.0040]:
        rows.append((f"BO 11+14 r={r}", run_with_blackouts("BO 11+14", [(11, 12), (14, 15)], r)))

    print("\n--- Risk fan: BO 11+14+08 ---")
    for r in [0.0032, 0.0034, 0.0036, 0.0038, 0.0040]:
        rows.append((f"BO 11+14+08 r={r}",
                     run_with_blackouts("BO 11+14+08", [(11, 12), (14, 15), (8, 9)], r)))

    print("\n=== TOP 20 by ratio (passing both targets first) ===")
    def sortkey(row):
        s = row[1]
        passes = s["max_dd_$"] < C.TARGET_MAX_DD and s["net_pnl"] >= C.TARGET_PNL_MIN
        return (-int(passes), -(s["net_pnl"] / max(s["max_dd_$"], 1.0)))
    rows.sort(key=sortkey)
    for label, s in rows[:20]:
        ratio = s["net_pnl"] / max(s["max_dd_$"], 1.0)
        mark = "✓" if s["max_dd_$"] < C.TARGET_MAX_DD and s["net_pnl"] >= C.TARGET_PNL_MIN else " "
        print(f"  {mark} {label:<30s}  ratio={ratio:>6.2f}  "
              f"PnL=${s['net_pnl']:>9,.0f}  DD=${s['max_dd_$']:>6,.0f}  "
              f"PF={s['profit_factor']}  N={s['trades']}")


if __name__ == "__main__":
    main()
