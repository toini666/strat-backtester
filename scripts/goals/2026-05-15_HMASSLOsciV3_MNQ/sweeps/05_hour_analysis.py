"""Step 5 — Trade bucket analysis: which hours/days are toxic?"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from _campaign import BEST_PARAMS, STRATEGY, SYMBOL, START, END, make_engine_settings
from scripts.goals._shared.harness import run_backtest
from scripts.goals._shared.analysis import bucket_by_hour, bucket_by_dow, print_hour_table, print_dow_table


def main() -> None:
    eng = make_engine_settings(STRATEGY, daily_loss_limit=1000.0)
    r = run_backtest(
        strategy_name=STRATEGY, symbol=SYMBOL, interval="3m",
        start=START, end=END,
        strategy_params=BEST_PARAMS,
        engine_settings=eng,
    )
    by_h = bucket_by_hour(r["trades"])
    by_d = bucket_by_dow(r["trades"])
    print("== PnL by hour (Brussels) ==")
    print_hour_table(by_h)
    print("\n== PnL by day-of-week (0=Mon) ==")
    print_dow_table(by_d)


if __name__ == "__main__":
    main()
