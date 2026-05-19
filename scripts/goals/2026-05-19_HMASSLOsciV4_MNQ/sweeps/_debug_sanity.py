"""Debug helper for Phase 1 drift — runs V3 with full V3 preset, V4 with
the V3-migrated params, and prints first-N trades for diff inspection."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from scripts.goals._shared.engine_settings import make_engine_settings
from scripts.goals._shared.harness import run_backtest, summarize, fmt_summary

from _campaign import (
    BASELINE_ACTIVE_BLACKOUTS,
    BASELINE_V4_PARAMS,
    END,
    INITIAL_EQUITY,
    MAX_CONTRACTS,
    RISK_PER_TRADE,
    START,
    SYMBOL,
)


# Full V3 winner preset strategy params (copied verbatim from the preset)
V3_PRESET_PARAMS = {
    "ema_len": 11,
    "hma1_len": 13,
    "hma2_len": 21,
    "amp_mult": 2.0,
    "hma_pol_bars": 0,
    "entry_window_bars": 3,
    "ssl_len": 80,
    "ssl_mult": 0.2,
    "hyper_wave_length": 7,
    "signal_type": "SMA",
    "signal_length": 4,
    "mf_length": 31,
    "mf_smooth": 7,
    "hw_dir_on": False,
    "hw_extreme_on": True,
    "hw_extreme": 20.0,
    "sig_extreme_on": True,
    "sig_extreme": 40,
    "hw_range_on": False,
    "hw_range": 10.0,
    "cloud_on": True,
    "delta_on": True,
    "cloud_zero_on": False,
    "delta_ext_on": False,
    "tick_buffer": 0,
    "max_sl_points": 300.0,
    "cooldown_bars": 3,
    "max_candle_pct": 0.9,
    "signal_candle_sl_on": False,
    "one_trade_per_entry_window": True,
    "hw_partial_pct": 0.0,
    "hw_partial_min_rr": 0.0,
    "block_loss_exit_before_partial": False,
    "final_exit_mode": "HMA rapide/SSL → HW",
    "final_exit_pct": 0.1,
}


def _engine(strategy):
    return make_engine_settings(
        strategy,
        extra_active_windows=BASELINE_ACTIVE_BLACKOUTS,
    )


def _common(strategy, params):
    return dict(
        strategy_name=strategy,
        symbol=SYMBOL,
        interval="7m",
        start=START,
        end=END,
        strategy_params=params,
        initial_equity=INITIAL_EQUITY,
        risk_per_trade=RISK_PER_TRADE,
        max_contracts=MAX_CONTRACTS,
        engine_settings=_engine(strategy),
    )


def main():
    print("=" * 100)
    print("DEBUG: V3 vs V4 baseline diff")
    print("=" * 100)

    rv3 = run_backtest(**_common("HMASSLOsciV3", V3_PRESET_PARAMS))
    sv3 = summarize(rv3)
    print(f"V3 (full preset)              {fmt_summary(sv3)}")

    rv4 = run_backtest(**_common("HMASSLOsciV4", BASELINE_V4_PARAMS))
    sv4 = summarize(rv4)
    print(f"V4 (V3-migrated, defaults)    {fmt_summary(sv4)}")

    print()
    print(f"PnL diff:    {sv4['net_pnl'] - sv3['net_pnl']:+,.2f}")
    print(f"DD diff:     {sv4['max_dd_$'] - sv3['max_dd_$']:+,.2f}")
    print(f"Trades diff: {sv4['trades'] - sv3['trades']:+d}")

    # Diff first-N trades to spot where they diverge
    v3_trades = [t for t in rv3["trades"] if not t.get("excluded")]
    v4_trades = [t for t in rv4["trades"] if not t.get("excluded")]
    print(f"\nActive trades: V3={len(v3_trades)}  V4={len(v4_trades)}")

    diverged = 0
    for i, (t3, t4) in enumerate(zip(v3_trades, v4_trades)):
        same_entry = (t3["entry_time"] == t4["entry_time"] and t3["side"] == t4["side"])
        same_exit = (t3["exit_time"] == t4["exit_time"]
                     and abs(t3["pnl"] - t4["pnl"]) < 0.01)
        if not (same_entry and same_exit):
            diverged += 1
            if diverged <= 10:
                print(f"\n  TRADE #{i+1} DIVERGES:")
                print(f"    V3  entry={t3['entry_time']} side={t3['side']:+d} "
                      f"exit={t3['exit_time']} reason={t3.get('exit_reason','?'):<20} "
                      f"pnl=${t3['pnl']:+,.2f}")
                print(f"    V4  entry={t4['entry_time']} side={t4['side']:+d} "
                      f"exit={t4['exit_time']} reason={t4.get('exit_reason','?'):<20} "
                      f"pnl=${t4['pnl']:+,.2f}")
    print(f"\nTotal diverging trades (paired): {diverged}/{min(len(v3_trades), len(v4_trades))}")


if __name__ == "__main__":
    main()
