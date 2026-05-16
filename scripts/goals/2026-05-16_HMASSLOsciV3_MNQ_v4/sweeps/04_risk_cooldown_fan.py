"""04 — Risk + cooldown fan on the top blackout combos.

Sweep 03 top picks (both targets passed):
  BO 11+14 r=0.0034     → $40,882 / $2,260 / ratio 18.09
  BO 11+14+08 r=0.0034  → $40,412 / $2,151 / ratio 18.79
  BO 11+14 r=0.0032     → $38,742 / $2,126 / ratio 18.22
  BO 11+14+08 r=0.0032  → $38,693 / $2,017 / ratio 19.18

Goal here:
  1. Tighter risk ladder (0.0033, 0.0035) — find where the DD wall is.
  2. Cooldown around 3: try {2, 3, 4} to see if it changes the risk ceiling.
  3. Try cd=2 to add trades back (1268 → maybe 1330+) at the new lower DD.

Sim count: ~30
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


def run(label, windows, risk=C.DEFAULT_RISK, params_override=None):
    es = make_engine_settings(
        C.STRATEGY,
        extra_active_windows=[_window_dict(s, e) for s, e in windows],
    )
    params = dict(C.V3_WINNER_PARAMS)
    if params_override:
        params.update(params_override)
    return bench(
        f"{label:<55s} r={risk:.4f}",
        strategy_name=C.STRATEGY, symbol=C.SYMBOL, interval=C.TF,
        start=C.START, end=C.END,
        strategy_params=params,
        initial_equity=C.INITIAL_EQUITY,
        risk_per_trade=risk,
        max_contracts=C.MAX_CONTRACTS,
        engine_settings=es,
    )


def main():
    print(f"=== 04 RISK + COOLDOWN FAN — TF={C.TF} ===\n")
    BO_2 = [(11, 12), (14, 15)]
    BO_3 = [(11, 12), (14, 15), (8, 9)]

    rows = []

    print("--- BO 11+14: tight risk ladder ---")
    for r in [0.0033, 0.0034, 0.0035]:
        rows.append((f"BO 11+14 r={r}", run("BO 11+14", BO_2, r)))

    print("\n--- BO 11+14+08: tight risk ladder ---")
    for r in [0.0033, 0.0034, 0.0035]:
        rows.append((f"BO 11+14+08 r={r}", run("BO 11+14+08", BO_3, r)))

    print("\n--- BO 11+14 cooldown sweep at r=0.0034 ---")
    for cd in [2, 3, 4]:
        rows.append((f"BO 11+14 cd={cd}", run("BO 11+14", BO_2, 0.0034, {"cooldown_bars": cd})))

    print("\n--- BO 11+14+08 cooldown sweep at r=0.0034 ---")
    for cd in [2, 3, 4]:
        rows.append((f"BO 11+14+08 cd={cd}", run("BO 11+14+08", BO_3, 0.0034, {"cooldown_bars": cd})))

    print("\n--- BO 11+14 cd=2 risk fan ---")
    for r in [0.0030, 0.0032, 0.0034, 0.0036, 0.0038]:
        rows.append((f"BO 11+14 cd=2 r={r}",
                     run("BO 11+14 cd=2", BO_2, r, {"cooldown_bars": 2})))

    print("\n--- BO 11+14+08 cd=2 risk fan ---")
    for r in [0.0030, 0.0032, 0.0034, 0.0036, 0.0038]:
        rows.append((f"BO 11+14+08 cd=2 r={r}",
                     run("BO 11+14+08 cd=2", BO_3, r, {"cooldown_bars": 2})))

    # cd=4 risk fan if cd=2 underperforms
    print("\n--- BO 11+14 cd=4 risk fan ---")
    for r in [0.0034, 0.0036, 0.0038, 0.0040]:
        rows.append((f"BO 11+14 cd=4 r={r}",
                     run("BO 11+14 cd=4", BO_2, r, {"cooldown_bars": 4})))

    print("\n=== TOP 25 by ratio (passing both targets first) ===")
    def sortkey(row):
        s = row[1]
        passes = s["max_dd_$"] < C.TARGET_MAX_DD and s["net_pnl"] >= C.TARGET_PNL_MIN
        return (-int(passes), -(s["net_pnl"] / max(s["max_dd_$"], 1.0)))
    rows.sort(key=sortkey)
    for label, s in rows[:25]:
        ratio = s["net_pnl"] / max(s["max_dd_$"], 1.0)
        mark = "✓" if s["max_dd_$"] < C.TARGET_MAX_DD and s["net_pnl"] >= C.TARGET_PNL_MIN else " "
        print(f"  {mark} {label:<40s}  ratio={ratio:>6.2f}  "
              f"PnL=${s['net_pnl']:>9,.0f}  DD=${s['max_dd_$']:>6,.0f}  "
              f"PF={s['profit_factor']}  N={s['trades']}")


if __name__ == "__main__":
    main()
