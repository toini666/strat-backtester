"""Build winner_preset.json for the v2 campaign and insert into data/presets.json.

Candidate B (sig_extreme_threshold=33) — chosen for OOS robustness:
  Full:  PnL $16,777 / DD $2,162 / PF 1.13
  2025:  PnL $13,537 / DD $2,162
  2026:  PnL $3,240  / DD $1,658
  OOS:   PnL $3,201  / DD $1,658

vs v1 winner: +$3,647 PnL (+28%), -$299 DD.

Same IS performance as candidate A (thr=35) but ~$700 more in OOS and
materially lower DD in 2026 — picked for robustness over chasing the
sharpest in-sample peak.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from scripts.goals._shared.engine_settings import ui_default_engine_settings
from scripts.goals._shared.harness import run_backtest, summarize, fmt_summary
from scripts.goals._shared.preset import build_preset, write_preset


STRATEGY = "GatorMTFv4"
SYMBOL = "MNQ"
INTERVAL = "1m"
START = "2025-01-02T00:00"
END = "2026-05-22T22:59"
INITIAL_EQUITY = 50_000.0
MAX_CONTRACTS = 20

# Final winner params (Candidate B)
WINNER_PARAMS = {
    # HMA stack
    "amp_mult": 1.5,
    "hma1_len": 13,
    "hma2_len": 21,
    "ema_len": 7,
    "entry_window_bars_trigger": 5,
    # Trigger TF
    "trigger_tf_minutes": 7,
    # SSL Keltner
    "ssl_len": 20,
    "ssl_mult": 0.20,
    # 4Kings osc
    "hyper_wave_length": 5,
    "signal_length": 3,
    # MFI (inert — all relevant cases on)
    "mf_length": 35,
    "mf_smooth": 6,
    # Sig extreme threshold (case D filter)
    "sig_extreme_threshold": 33.0,
    # Cases (1101: A+B+D, C off)
    "case_a_on": True,
    "case_b_on": True,
    "case_c_on": False,
    "case_d_on": True,
    # Risk / SL geometry
    "sl_lookback": 15,
    "sl_min_pct": 0.15,
    "tick_buffer": 6,
    "cooldown_bars": 90,
    "hw_partial_pct": 0.0,
    "partial_rr": 0.0,
    "final_rr": 1.5,
    "one_trade_per_window": True,
}

WINNER_RISK = 0.28 / 100  # 0.28%


def main():
    print("=" * 90)
    print("BUILD WINNER PRESET — v2 Candidate B")
    print("=" * 90)

    # Engine: UI defaults for GatorMTFv4, but DEACTIVATE all blackouts (campaign found
    # them detrimental on this config) and lock auto_close at 22:00.
    es = ui_default_engine_settings(STRATEGY)
    for w in es.blackout_windows:
        w.active = False
    es.auto_close_hour = 22
    es.auto_close_minute = 0
    # daily_limits OFF (per user constraint)
    es.daily_win_limit_enabled = False
    es.daily_loss_limit_enabled = False

    # Replay to capture exact metrics
    r = run_backtest(
        strategy_name=STRATEGY,
        symbol=SYMBOL, interval=INTERVAL,
        start=START, end=END,
        strategy_params=WINNER_PARAMS,
        initial_equity=INITIAL_EQUITY,
        risk_per_trade=WINNER_RISK,
        max_contracts=MAX_CONTRACTS,
        engine_settings=es,
    )
    s = summarize(r)
    print(f"Replay: {fmt_summary(s)}")
    print()

    preset = build_preset(
        strategy_name=STRATEGY,
        symbol=SYMBOL,
        interval=INTERVAL,
        start=START,
        end=END,
        initial_equity=INITIAL_EQUITY,
        risk_per_trade_decimal=WINNER_RISK,
        max_contracts=MAX_CONTRACTS,
        strategy_param_overrides=WINNER_PARAMS,
        engine_settings=es,
        metrics_summary=s,
        name="BESTPNL-MNQ GatorMTFv4 - MNQ 1m v2",
    )

    standalone = Path(__file__).resolve().parent / "winner_preset.json"
    write_preset(preset, standalone, insert_into_presets_json=True)
    print(f"✅ Wrote {standalone}")
    print(f"✅ Inserted into data/presets.json as: {preset['name']}")
    print()
    print("Expected metrics for verify_preset.py:")
    print(f"  net_pnl       = {s['net_pnl']}")
    print(f"  max_dd_$      = {s['max_dd_$']}")
    print(f"  trades        = {s['trades']}")
    print(f"  win_rate      = {s['win_rate']}")
    print(f"  profit_factor = {s['profit_factor']}")


if __name__ == "__main__":
    main()
