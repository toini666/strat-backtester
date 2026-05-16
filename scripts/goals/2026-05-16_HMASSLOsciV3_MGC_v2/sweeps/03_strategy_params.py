"""Sweep 03 — Strategy params 1D.

Baseline = prev_winner_overrides + block_loss_exit_before_partial=True (from sweep 02).
For each hyper-param, sweep a range of values, keep others at baseline.
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

# v2 baseline = prev winner + block_loss_exit_before_partial
BASELINE = dict(PREV_WINNER_OVERRIDES)
BASELINE["block_loss_exit_before_partial"] = True


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


def sweep(name, values):
    print("-" * 110)
    print(f"## Sweep {name}: {values}")
    for v in values:
        cfg = dict(BASELINE)
        cfg[name] = v
        run_one(f"{name}={v}", cfg)


if __name__ == "__main__":
    print("=" * 110)
    print("Sweep 03 — Strategy params 1D")
    print(f"Baseline overrides: {BASELINE}")
    print("=" * 110)
    run_one("BASELINE", BASELINE)

    # HMA Ribbon
    sweep("ema_len", [5, 7, 9, 13, 17, 21])
    sweep("hma1_len", [7, 9, 13, 17, 21])
    sweep("hma2_len", [17, 21, 26, 30, 34, 42, 50])
    sweep("amp_mult", [1.0, 1.5, 2.0, 2.5, 3.0])
    sweep("hma_pol_bars", [0, 1, 2, 3, 5, 7, 10])
    sweep("entry_window_bars", [1, 2, 3, 5, 8, 12])

    # SSL Channel
    sweep("ssl_len", [30, 40, 60, 80, 100, 120])
    sweep("ssl_mult", [0.05, 0.1, 0.2, 0.3, 0.5])

    # 4Kings Oscillator
    sweep("hyper_wave_length", [3, 4, 5, 6, 7, 9])
    sweep("signal_length", [1, 2, 3, 4, 5])

    # MFI / cloud
    sweep("mf_length", [15, 25, 35, 45, 60])
    sweep("mf_smooth", [3, 4, 6, 8, 12])

    # Oscillator filter thresholds
    sweep("hw_extreme", [10.0, 15.0, 20.0, 25.0, 30.0])
    sweep("sig_extreme", [20.0, 25.0, 35.0, 45.0])
    sweep("hw_range", [3.0, 5.0, 10.0, 15.0, 20.0])

    # Risk management
    sweep("max_sl_points", [50.0, 100.0, 150.0, 200.0, 300.0, 500.0])
    sweep("cooldown_bars", [0, 1, 2, 3, 5])
    sweep("max_candle_pct", [0.0, 0.3, 0.5, 0.7, 0.9, 1.5])
    sweep("tick_buffer", [0, 1, 2, 3])
