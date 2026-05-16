"""07 — Finetune: combine the top 03b movers + risk fan.

From sweep 03b, the winning levers were:
  - cooldown=3 (the breakthrough: $37,381 / $2,567 / ratio 14.56)
  - sig_extreme=40 (small DD reduction, slight PnL improvement)
  - max_sl=250 (small PnL improvement, neutral DD)
  - hw_partial_pct=50 rr=0.5 (DD ↓ but PnL ↓)

We combine the orthogonal improvers and fan the risk to find the
sweet spot that passes BOTH targets simultaneously:
  - Net PnL ≥ 35,000 (goal ≥ 40,000)
  - Max DD < 2,500

Note `cooldown=3` is the breakthrough. The other tweaks add marginal benefit.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _campaign as C  # noqa: E402

from scripts.goals._shared.harness import bench  # noqa: E402


TF = "7m"
BASE = dict(C.PREV_WINNER_PARAMS)
BASE["hw_dir_on"] = False  # sweep 02


def run(label, overrides, risk=C.DEFAULT_RISK):
    params = dict(BASE)
    params.update(overrides)
    return bench(
        f"{label:<55s} r={risk:.4f}",
        strategy_name=C.STRATEGY, symbol=C.SYMBOL, interval=TF,
        start=C.START, end=C.END, strategy_params=params,
        initial_equity=C.INITIAL_EQUITY, risk_per_trade=risk,
        max_contracts=C.MAX_CONTRACTS,
    )


def main():
    print(f"=== 07 FINETUNE — TF={TF} ===\n")
    print(f"BASE = v2_winner + hw_dir_on=False\n")

    rows = []
    rows.append(("REF base", run("REF base", {})))

    # --- Single best lever: cooldown=3 ---
    print("\n--- cooldown=3 alone (risk fan) ---")
    cd3 = {"cooldown_bars": 3}
    for r in [0.0028, 0.0030, 0.0032, 0.0033, 0.0034, 0.0035, 0.0036]:
        rows.append((f"cd=3 r={r}", run(f"cd=3", cd3, r)))

    # --- cooldown=3 + sx=40 ---
    print("\n--- cd=3 + sx=40 (risk fan) ---")
    cd3_sx40 = {"cooldown_bars": 3, "sig_extreme": 40}
    for r in [0.0028, 0.0030, 0.0032, 0.0033, 0.0034, 0.0035, 0.0036]:
        rows.append((f"cd=3 sx=40 r={r}", run(f"cd=3 sx=40", cd3_sx40, r)))

    # --- cooldown=3 + max_sl=250 ---
    print("\n--- cd=3 + max_sl=250 (risk fan) ---")
    cd3_msl = {"cooldown_bars": 3, "max_sl_points": 250.0}
    for r in [0.0028, 0.0030, 0.0032, 0.0033, 0.0034, 0.0035, 0.0036]:
        rows.append((f"cd=3 msl=250 r={r}", run(f"cd=3 msl=250", cd3_msl, r)))

    # --- cooldown=3 + sx=40 + max_sl=250 ---
    print("\n--- cd=3 + sx=40 + max_sl=250 (risk fan) ---")
    cd3_sx40_msl = {"cooldown_bars": 3, "sig_extreme": 40, "max_sl_points": 250.0}
    for r in [0.0028, 0.0030, 0.0032, 0.0033, 0.0034, 0.0035, 0.0036]:
        rows.append((f"cd=3 sx=40 msl=250 r={r}",
                     run(f"cd=3 sx=40 msl=250", cd3_sx40_msl, r)))

    # --- cooldown=3 + hw_part=50 rr=0.5 (DD reducer combo) ---
    print("\n--- cd=3 + hw_part=50 rr=0.5 ---")
    cd3_hw = {"cooldown_bars": 3, "hw_partial_pct": 50.0, "hw_partial_min_rr": 0.5}
    for r in [0.0032, 0.0034, 0.0036, 0.0038, 0.0040]:
        rows.append((f"cd=3 hw50/.5 r={r}", run(f"cd=3 hw50/.5", cd3_hw, r)))

    # --- All three combined ---
    print("\n--- cd=3 + sx=40 + max_sl=250 + hw50/.5 ---")
    full = {"cooldown_bars": 3, "sig_extreme": 40, "max_sl_points": 250.0,
            "hw_partial_pct": 50.0, "hw_partial_min_rr": 0.5}
    for r in [0.0034, 0.0036, 0.0038, 0.0040]:
        rows.append((f"FULL r={r}", run(f"FULL combo", full, r)))

    print("\n=== TOP 25 (passing both targets first) ===")
    def sortkey(row):
        s = row[1]
        passes = s["max_dd_$"] < C.TARGET_MAX_DD and s["net_pnl"] >= C.TARGET_PNL_MIN
        return (-int(passes), -(s["net_pnl"] / max(s["max_dd_$"], 1.0)))
    rows.sort(key=sortkey)
    for label, s in rows[:25]:
        ratio = s["net_pnl"] / max(s["max_dd_$"], 1.0)
        mark = "✓" if s["max_dd_$"] < C.TARGET_MAX_DD and s["net_pnl"] >= C.TARGET_PNL_MIN else " "
        print(f"  {mark} {label:<55s}  ratio={ratio:>6.2f}  "
              f"PnL=${s['net_pnl']:>9,.0f}  DD=${s['max_dd_$']:>6,.0f}  "
              f"PF={s['profit_factor']}  N={s['trades']}")


if __name__ == "__main__":
    main()
