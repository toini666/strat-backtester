"""Sweep 02 — Filter activation.

Starting from prev_winner_overrides (hma2_len=34, hw_range_on=True) at 7m,
risk=0.52%, with ONLY 22-23:59 active, toggle each optional filter ON/OFF to
see if any individual lever improves P/DD.
"""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from scripts.goals._shared.harness import run_backtest, summarize, fmt_summary
from scripts.goals._shared.engine_settings import ui_default_engine_settings

from _campaign import (
    STRATEGY, SYMBOL, INTERVAL, START, END, INITIAL_EQUITY, MAX_CONTRACTS,
    PREV_WINNER_OVERRIDES, PREV_WINNER_RISK, pdd,
)

ES = ui_default_engine_settings(STRATEGY)


def run_one(label, params):
    r = run_backtest(
        strategy_name=STRATEGY, symbol=SYMBOL, interval=INTERVAL,
        start=START, end=END, strategy_params=params,
        initial_equity=INITIAL_EQUITY, risk_per_trade=PREV_WINNER_RISK,
        max_contracts=MAX_CONTRACTS, engine_settings=ES,
    )
    s = summarize(r)
    s["label"] = label
    p_dd = pdd(s["net_pnl"], s["max_dd_$"])
    print(f"{label:<60s} {fmt_summary(s)}  P/DD={p_dd:5.2f}")
    return s


if __name__ == "__main__":
    print("=" * 110)
    print("Sweep 02 — Filter activation (baseline = prev_winner_overrides @ 7m, 22-23:59 only)")
    print("=" * 110)

    base = dict(PREV_WINNER_OVERRIDES)
    run_one("baseline (hma2=34 + hw_range_on)", base)
    print("-" * 110)

    # Toggle each boolean filter
    toggle_filters = [
        ("hw_dir_on", False),     # default True
        ("hw_extreme_on", False), # default True
        ("sig_extreme_on", False),# default True
        ("hw_range_on", False),   # we have True, see effect of OFF
        ("cloud_on", True),       # default False
        ("delta_on", False),      # default True
        ("cloud_zero_on", True),  # default False
        ("delta_ext_on", True),   # default False
        ("signal_candle_sl_on", True),  # default False
        ("one_trade_per_entry_window", False),  # default True
        ("block_loss_exit_before_partial", True),  # default False
    ]
    for k, v in toggle_filters:
        cfg = dict(base)
        cfg[k] = v
        run_one(f"{k}={v}", cfg)
