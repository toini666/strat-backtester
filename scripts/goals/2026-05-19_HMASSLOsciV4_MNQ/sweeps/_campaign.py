"""Campaign-local constants for 2026-05-19 HMASSLOsciV4 MNQ.

Single source of truth for: strategy, symbol, period, baseline V3-migrated V4 params.
"""

from __future__ import annotations

STRATEGY = "HMASSLOsciV4"
SYMBOL = "MNQ"
INTERVAL = "7m"
START = "2025-01-06T00:00"
END = "2026-05-15T00:00"
INITIAL_EQUITY = 50_000.0
MAX_CONTRACTS = 50
RISK_PER_TRADE = 0.0048  # 0.48% — V3 baseline

# V3 baseline metrics — re-measured 2026-05-19 with current engine (Topstep
# $0.50/RT commission was added post-V5-winner, hence drift from the originally
# documented $68.8k / $1.6k). V4 with V3-migrated params + neutral defaults
# reproduces this exactly (sanity-check Phase 1 confirmed).
V3_BASELINE = {
    "net_pnl": 66_679,
    "max_dd_$": 1_617,
    "trades": 1_241,
    "win_rate": 47.9,
    "profit_factor": 1.67,
}

# Originally documented baseline (in mission file) — kept for reference.
V3_BASELINE_DOC = {
    "net_pnl": 68_765,
    "max_dd_$": 1_579,
    "trades": 1_241,
    "win_rate": 48.3,
    "profit_factor": 1.70,
}

# Mission cap (strict)
MAX_DD_BUDGET = 2_000.0

# V3 → V4 migrated params. Only the keys that EXIST in V4 default_params are kept.
# Dropped V3-only keys: hw_partial_pct, hw_partial_min_rr, block_loss_exit_before_partial,
#                       final_exit_mode, final_exit_pct, signal_candle_sl_on.
# Translated: signal_candle_sl_on=False → reject_entry_at_sl_extreme=False
#             (bit-identical only because tick_buffer=0; flag this if sweeping tick_buffer).
# 9 V4-new keys left at their neutral defaults (reproduce V3 by construction).
BASELINE_V4_PARAMS = {
    # HMA Ribbon
    "ema_len": 11,
    "hma1_len": 13,
    "hma2_len": 21,
    "amp_mult": 2.0,
    "hma_pol_bars": 0,
    "entry_window_bars": 3,
    # SSL Channel
    "ssl_len": 80,
    "ssl_mult": 0.2,
    # 4Kings Oscillator
    "hyper_wave_length": 7,
    "signal_type": "SMA",
    "signal_length": 4,
    # Smart Money Flow
    "mf_length": 31,
    "mf_smooth": 7,
    # Oscillator filters
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
    # Risk management (strategy-internal)
    "tick_buffer": 0,
    "max_sl_points": 300.0,
    "cooldown_bars": 3,
    "max_candle_pct": 0.9,
    # V4 renamed (V3-compat: False == V3's signal_candle_sl_on=False)
    "reject_entry_at_sl_extreme": False,
    "one_trade_per_entry_window": True,
    # 9 V4-new exit/entry levers — neutral defaults reproduce V3
    "move_to_be_on_fast_hma_cross": False,
    "final_exit_min_rr": 0.0,
    "move_to_be_on_rejected_exit": False,
    "early_exit_fired_mode": "off",
    "block_entry_if_both_windows": False,
    "tp_mode_fast_hma_hw": True,
    "tp_mode_slow_hma_cross": False,
    "report_tp_if_mfi_ok": False,
}

# Baseline V3 winner's 5 active blackouts (reference Brussels) — applied via
# make_engine_settings(extra_active_windows=...) on top of the V4 UI-default
# engine settings (which only ship the 22:00-23:59 blackout active).
BASELINE_ACTIVE_BLACKOUTS = [
    {"start_hour": 8,  "start_minute": 0, "end_hour": 9,  "end_minute": 0},
    {"start_hour": 11, "start_minute": 0, "end_hour": 12, "end_minute": 0},
    {"start_hour": 12, "start_minute": 0, "end_hour": 13, "end_minute": 0},
    {"start_hour": 14, "start_minute": 0, "end_hour": 15, "end_minute": 0},
    # 22:00-23:59 is already active by default in V4 UI defaults.
]
