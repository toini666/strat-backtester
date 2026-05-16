"""04 — Risk + daily limits, starting from sweep 03 best combo.

Per advisor: with v2's hourly blackouts removed, daily LOSS limits are the
natural substitute. Test both intra_bar and after_close.

Risk sweep is secondary — pure risk scaling can't push ratio up; we use it
only to fine-tune the level around the targets once a high-ratio combo
is found.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _campaign as C  # noqa: E402

from scripts.goals._shared.engine_settings import make_engine_settings  # noqa: E402
from scripts.goals._shared.harness import bench  # noqa: E402


TF = "7m"

# Best params from sweeps 02+03 (filled in by 03's output).
# For now, use v2_winner + hw_dir_on=False as a placeholder.
BEST_PARAMS = dict(C.PREV_WINNER_PARAMS)
BEST_PARAMS["hw_dir_on"] = False


def main():
    print(f"=== 04 RISK + DAILY LIMITS — TF={TF} ===\n")

    rows = []

    # --- Risk sweep (no daily limits) ---
    print("--- Risk sweep (no daily limits) ---")
    for r in [0.0024, 0.0028, 0.0030, 0.0032, 0.0034, 0.0036, 0.0040, 0.0045, 0.005]:
        rows.append((f"risk={r}", bench(
            f"{'risk='+str(r):<35s}",
            strategy_name=C.STRATEGY, symbol=C.SYMBOL, interval=TF,
            start=C.START, end=C.END, strategy_params=BEST_PARAMS,
            initial_equity=C.INITIAL_EQUITY, risk_per_trade=r,
            max_contracts=C.MAX_CONTRACTS,
        )))

    print("\n--- Daily limits intra_bar (loss only) ---")
    for win, loss in [(None, 700), (None, 900), (None, 1100), (None, 1300), (None, 1500),
                      (None, 1800), (None, 2000)]:
        es = make_engine_settings(
            C.STRATEGY,
            daily_loss_limit=loss,
            daily_limit_mode="intra_bar",
        )
        rows.append((f"dlim_intra L={loss}", bench(
            f"{'dlim_intra L='+str(loss):<35s}",
            strategy_name=C.STRATEGY, symbol=C.SYMBOL, interval=TF,
            start=C.START, end=C.END, strategy_params=BEST_PARAMS,
            initial_equity=C.INITIAL_EQUITY, risk_per_trade=C.DEFAULT_RISK,
            max_contracts=C.MAX_CONTRACTS, engine_settings=es,
        )))

    print("\n--- Daily limits intra_bar (loss + win) ---")
    for win, loss in [(800, 1100), (1000, 1100), (1200, 1300), (1500, 1500),
                      (2000, 1800)]:
        es = make_engine_settings(
            C.STRATEGY,
            daily_win_limit=win, daily_loss_limit=loss,
            daily_limit_mode="intra_bar",
        )
        rows.append((f"dlim_intra W={win} L={loss}", bench(
            f"{'dlim_intra W='+str(win)+' L='+str(loss):<35s}",
            strategy_name=C.STRATEGY, symbol=C.SYMBOL, interval=TF,
            start=C.START, end=C.END, strategy_params=BEST_PARAMS,
            initial_equity=C.INITIAL_EQUITY, risk_per_trade=C.DEFAULT_RISK,
            max_contracts=C.MAX_CONTRACTS, engine_settings=es,
        )))

    print("\n--- Daily limits after_close (loss only) ---")
    for loss in [900, 1100, 1300, 1500, 1800]:
        es = make_engine_settings(
            C.STRATEGY,
            daily_loss_limit=loss,
            daily_limit_mode="after_close",
        )
        rows.append((f"dlim_close L={loss}", bench(
            f"{'dlim_close L='+str(loss):<35s}",
            strategy_name=C.STRATEGY, symbol=C.SYMBOL, interval=TF,
            start=C.START, end=C.END, strategy_params=BEST_PARAMS,
            initial_equity=C.INITIAL_EQUITY, risk_per_trade=C.DEFAULT_RISK,
            max_contracts=C.MAX_CONTRACTS, engine_settings=es,
        )))

    print("\n=== Ranked by Profit/DD ratio (subject to both targets) ===")
    rows.sort(key=lambda x: x[1]["net_pnl"] / max(x[1]["max_dd_$"], 1.0), reverse=True)
    for label, s in rows:
        ratio = s["net_pnl"] / max(s["max_dd_$"], 1.0)
        mark = "✓" if s["max_dd_$"] < C.TARGET_MAX_DD and s["net_pnl"] >= C.TARGET_PNL_MIN else " "
        print(f"  {mark} {label:<35s}  ratio={ratio:>6.2f}  "
              f"PnL=${s['net_pnl']:>9,.0f}  DD=${s['max_dd_$']:>6,.0f}  "
              f"PF={s['profit_factor']}  N={s['trades']}")


if __name__ == "__main__":
    main()
