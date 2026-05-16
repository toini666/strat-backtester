"""07 — Final fine-tune. Close the gap on the leading candidate.

Sweep 06 top candidates:
  ema=11 BO 11+14 r=0.0036          → $50,770 / $2,268 / ratio 22.39  (margin $232)
  ema=11 mf=35 BO 11+14+08 r=0.0034 → $51,343 / $2,443 / ratio 21.02  (margin $57 - tight)
  ema=11 BO 11+14+08 r=0.0036       → $50,189 / $2,431 / ratio 20.65  (margin $69)
  ema=11 r=0.0044 BO 11+14+08       → $60,304 / $2,909                (DD over)

Per advisor:
  - Untested cross: ema=11 + mf=35 + BO 11+14 (the cell we missed)
  - Risk fan gap on ema=11 BO 11+14: try r=0.0037, 0.0038
  - Sanity check: ema=11 no-blackouts at r=0.0034
  - hpb=1 was near-best in sweep 05 — try it
  - Effective DD target = $2,400 (replay variance safety)

Sim count: ~10
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


def run(label, windows, overrides, risk):
    es = make_engine_settings(
        C.STRATEGY,
        extra_active_windows=[_window_dict(s, e) for s, e in windows],
    )
    params = dict(C.V3_WINNER_PARAMS)
    params.update(overrides)
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
    print(f"=== 07 FINETUNE — close the gap ===\n")
    BO_2 = [(11, 12), (14, 15)]
    BO_3 = [(11, 12), (14, 15), (8, 9)]
    NO_BO = []

    rows = []

    print("--- The missing cell: ema=11 + mf=35 + BO 11+14 ---")
    for r in [0.0034, 0.0036, 0.0038]:
        rows.append((f"ema=11 mf=35 BO 11+14 r={r}",
                     run("ema=11 mf=35 BO 11+14", BO_2,
                         {"ema_len": 11, "mf_length": 35}, r)))

    print("\n--- ema=11 BO 11+14 risk push ---")
    for r in [0.0037, 0.0038]:
        rows.append((f"ema=11 BO 11+14 r={r}",
                     run("ema=11 BO 11+14", BO_2, {"ema_len": 11}, r)))

    print("\n--- ema=11 + hpb=1 on best BO ---")
    rows.append(("ema=11 hpb=1 BO 11+14 r=0.0036",
                 run("ema=11 hpb=1 BO 11+14", BO_2,
                     {"ema_len": 11, "hma_pol_bars": 1}, 0.0036)))
    rows.append(("ema=11 hpb=1 BO 11+14+08 r=0.0034",
                 run("ema=11 hpb=1 BO 11+14+08", BO_3,
                     {"ema_len": 11, "hma_pol_bars": 1}, 0.0034)))

    print("\n--- Sanity: ema=11 NO BLACKOUT ---")
    rows.append(("ema=11 noBO r=0.0034",
                 run("ema=11 noBO", NO_BO, {"ema_len": 11}, 0.0034)))
    rows.append(("ema=11 noBO r=0.0036",
                 run("ema=11 noBO", NO_BO, {"ema_len": 11}, 0.0036)))

    print("\n=== TOP 15 (passing SAFE target $2,400 first) ===")
    def sortkey(row):
        s = row[1]
        passes = s["max_dd_$"] < C.SAFE_MAX_DD and s["net_pnl"] >= C.TARGET_PNL_MIN
        return (-int(passes), -(s["net_pnl"] / max(s["max_dd_$"], 1.0)))
    rows.sort(key=sortkey)
    for label, s in rows[:15]:
        ratio = s["net_pnl"] / max(s["max_dd_$"], 1.0)
        margin = C.TARGET_MAX_DD - s["max_dd_$"]
        mark = "✓✓" if (s["max_dd_$"] < C.SAFE_MAX_DD and s["net_pnl"] >= C.TARGET_PNL_MIN) else (
            "✓ " if (s["max_dd_$"] < C.TARGET_MAX_DD and s["net_pnl"] >= C.TARGET_PNL_MIN) else "  ")
        print(f"  {mark} {label:<42s}  ratio={ratio:>6.2f}  "
              f"PnL=${s['net_pnl']:>9,.0f}  DD=${s['max_dd_$']:>6,.0f} (margin ${margin:>4,.0f})  "
              f"PF={s['profit_factor']}  N={s['trades']}")


if __name__ == "__main__":
    main()
