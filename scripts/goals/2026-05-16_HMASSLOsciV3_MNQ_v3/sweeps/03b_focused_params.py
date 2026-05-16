"""03b — Focused 1-D + combo on the params most likely to move the needle.

Sweep 03 was killed mid-flight (only signal_length + sig_extreme finished).
This focused sweep covers:

 - sig_extreme: 30, 35, 40       (40 looked best in sweep 03)
 - hw_partial_pct × hw_partial_min_rr
 - final_exit_mode × final_exit_pct
 - signal_candle_sl_on (combined with hw_dir_on=False)
 - block_loss_exit_before_partial (combined)
 - tick_buffer
 - max_sl_points (tighter)
 - cooldown_bars (longer)

All from BASE = v2_winner + hw_dir_on=False.
"""

from __future__ import annotations

import sys
from pathlib import Path
from itertools import product

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _campaign as C  # noqa: E402

from scripts.goals._shared.harness import bench  # noqa: E402


TF = "7m"
BASE = dict(C.PREV_WINNER_PARAMS)
BASE["hw_dir_on"] = False


def run(label, overrides):
    params = dict(BASE)
    params.update(overrides)
    return bench(
        f"{label:<55s}",
        strategy_name=C.STRATEGY, symbol=C.SYMBOL, interval=TF,
        start=C.START, end=C.END, strategy_params=params,
        initial_equity=C.INITIAL_EQUITY, risk_per_trade=C.DEFAULT_RISK,
        max_contracts=C.MAX_CONTRACTS,
    )


def main():
    print(f"=== 03b FOCUSED PARAMS — TF={TF} ===\n")
    print(f"Base = v2_winner + hw_dir_on=False  (REF $36.6k / $2.8k)\n")
    rows = []
    rows.append(("REF base", run("REF base", {})))

    print("\n--- sig_extreme + cloud_on=False (check no cloud combo) ---")
    for sx in [30, 35, 40]:
        rows.append((f"sx={sx}", run(f"sx={sx}", {"sig_extreme": sx})))
    rows.append(("sx=40 +cloud_off", run("sx=40 cloud_off", {"sig_extreme": 40, "cloud_on": False})))

    print("\n--- hw_partial_pct × hw_partial_min_rr ---")
    for pct in [0.0, 25.0, 50.0]:
        for minrr in [0.0, 0.5, 1.0]:
            rows.append((f"hw_part={pct} rr={minrr}",
                         run(f"hw_part={pct} rr={minrr}",
                             {"hw_partial_pct": pct, "hw_partial_min_rr": minrr})))

    print("\n--- final_exit_mode × final_exit_pct ---")
    for fpct in [0.05, 0.1, 0.15, 0.2, 0.3]:
        rows.append((f"final_fixed pct={fpct}",
                     run(f"final_fixed pct={fpct}",
                         {"final_exit_mode": "% du prix d'entrée en profit",
                          "final_exit_pct": fpct})))

    print("\n--- signal_candle_sl_on + block_loss combos ---")
    rows.append(("scsl=True", run("scsl=True", {"signal_candle_sl_on": True})))
    rows.append(("blkloss=True", run("blkloss=True", {"block_loss_exit_before_partial": True})))
    rows.append(("scsl + blkloss",
                 run("scsl + blkloss",
                     {"signal_candle_sl_on": True, "block_loss_exit_before_partial": True})))
    rows.append(("scsl + sx=40",
                 run("scsl + sx=40",
                     {"signal_candle_sl_on": True, "sig_extreme": 40})))

    print("\n--- tick_buffer + max_sl_points ---")
    for tb in [0, 1, 2, 3]:
        rows.append((f"tick_buf={tb}", run(f"tick_buf={tb}", {"tick_buffer": tb})))
    for msl in [100.0, 150.0, 200.0, 250.0]:
        rows.append((f"max_sl={msl}", run(f"max_sl={msl}", {"max_sl_points": msl})))

    print("\n--- cooldown_bars ---")
    for cd in [0, 1, 2, 3, 5]:
        rows.append((f"cooldown={cd}", run(f"cooldown={cd}", {"cooldown_bars": cd})))

    print("\n=== TOP 20 by ratio (passing both targets first) ===")
    def sortkey(row):
        s = row[1]
        passes = s["max_dd_$"] < C.TARGET_MAX_DD and s["net_pnl"] >= C.TARGET_PNL_MIN
        return (-int(passes), -(s["net_pnl"] / max(s["max_dd_$"], 1.0)))
    rows.sort(key=sortkey)
    for label, s in rows[:20]:
        ratio = s["net_pnl"] / max(s["max_dd_$"], 1.0)
        mark = "✓" if s["max_dd_$"] < C.TARGET_MAX_DD and s["net_pnl"] >= C.TARGET_PNL_MIN else " "
        print(f"  {mark} {label:<55s}  ratio={ratio:>6.2f}  "
              f"PnL=${s['net_pnl']:>9,.0f}  DD=${s['max_dd_$']:>6,.0f}  "
              f"PF={s['profit_factor']}  N={s['trades']}")


if __name__ == "__main__":
    main()
