"""02 — Filter activation, starting from v2_winner params on TF=7m.

Each variant toggles ONE filter at a time relative to v2_winner.
Goal: find filter changes that reduce DD without killing PnL.

Filters considered (booleans):
  - hw_dir_on, hw_extreme_on, sig_extreme_on, hw_range_on
  - cloud_on, delta_on, cloud_zero_on, delta_ext_on
  - signal_candle_sl_on  (SL based on signal candle, may tighten/reduce DD)
  - one_trade_per_entry_window
  - block_loss_exit_before_partial
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _campaign as C  # noqa: E402

from scripts.goals._shared.harness import bench  # noqa: E402


TF = "7m"
BASE = C.PREV_WINNER_PARAMS

FLAGS_TO_TOGGLE = [
    "hw_dir_on", "hw_extreme_on", "sig_extreme_on", "hw_range_on",
    "cloud_on", "delta_on", "cloud_zero_on", "delta_ext_on",
    "signal_candle_sl_on", "one_trade_per_entry_window",
    "block_loss_exit_before_partial",
]


def main():
    print(f"=== 02 FILTER ACTIVATION — TF={TF} ===\n")

    # Reference run
    rows = []
    rows.append(("REF v2_winner", bench(
        f"{'REF v2_winner':<35s}",
        strategy_name=C.STRATEGY, symbol=C.SYMBOL, interval=TF,
        start=C.START, end=C.END, strategy_params=BASE,
        initial_equity=C.INITIAL_EQUITY, risk_per_trade=C.DEFAULT_RISK,
        max_contracts=C.MAX_CONTRACTS,
    )))

    print()
    for flag in FLAGS_TO_TOGGLE:
        current = BASE.get(flag, False)
        flipped = not current
        params = dict(BASE)
        params[flag] = flipped
        label = f"{flag}={flipped}"
        rows.append((label, bench(
            f"{label:<35s}",
            strategy_name=C.STRATEGY, symbol=C.SYMBOL, interval=TF,
            start=C.START, end=C.END, strategy_params=params,
            initial_equity=C.INITIAL_EQUITY, risk_per_trade=C.DEFAULT_RISK,
            max_contracts=C.MAX_CONTRACTS,
        )))

    print("\n--- Ranked by Profit/DD ratio ---")
    ranked = sorted(rows, key=lambda x: x[1]["net_pnl"] / max(x[1]["max_dd_$"], 1.0),
                    reverse=True)
    for label, s in ranked:
        ratio = s["net_pnl"] / max(s["max_dd_$"], 1.0)
        flag_passes_dd = s["max_dd_$"] < C.TARGET_MAX_DD
        flag_passes_pnl = s["net_pnl"] >= C.TARGET_PNL_MIN
        marks = ("✓" if flag_passes_dd else " ") + ("✓" if flag_passes_pnl else " ")
        print(f"  {marks} {label:<40s} ratio={ratio:>6.2f}  "
              f"PnL=${s['net_pnl']:>9,.0f}  DD=${s['max_dd_$']:>6,.0f}  "
              f"PF={s['profit_factor']}  N={s['trades']}")


if __name__ == "__main__":
    main()
