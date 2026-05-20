"""Campaign constants for 2026-05-20 MomentumCheckerV2 MNQ 7m — v2.

Re-run after the simulator `max_drawdown_dollars` bug was patched. The
original campaign optimised against the buggy metric; this v2 campaign
optimises against the corrected $-DD = max peak-to-trough drawdown in $.

NEW BASELINE — "B combo" identified by Phase 11 re-rank of the v1 campaign:
  amp_mult=3.0, max_candle_pct=0.3, sig_extreme=40 (filter ON), sl_max_points=60
  risk = 0.55%
  Result: PnL=$71,371 / $DD=$2,900 / %DD=4.43% / N=781 / WR=41.0% / PF=1.63
  → beats V1 anchor (PnL=$61,313 / $DD=$3,074) by +$10,058 PnL, -$174 $DD

Hard ceiling: $DD ≤ V1 anchor's TRUE $DD = $3,074
Target:       $DD < $2,000
Goal:         maximise PnL within these constraints

Fixed by user constraint:
  - symbol  = MNQ
  - tf      = 7m
  - period  = 2025-01-07 → 2026-05-15
  - max contracts = 20
  - no daily win/loss limits
  - auto_close = 22:00 (CME close, reference Brussels)
  - daily limits: OFF
"""

from __future__ import annotations

STRATEGY = "MomentumCheckerV2"
SYMBOL = "MNQ"
INTERVAL = "7m"

START = "2025-01-07T00:00"
END   = "2026-05-15T22:59"

INITIAL_EQUITY = 50_000.0
MAX_CONTRACTS = 20

# New baseline risk — B combo's sweet spot in the Phase 11 re-rank
RISK_PER_TRADE = 0.0055

# Strict $DD constraints
DD_CEILING = 3_074.0    # V1 anchor's TRUE $DD
DD_TARGET = 2_000.0     # user-stated soft target

# New baseline metrics (B combo @ 0.55%, patched simulator)
BASELINE_PNL = 71_371.0
BASELINE_DD = 2_900.0
BASELINE_TRADES = 781
BASELINE_WR = 41.0
BASELINE_PF = 1.63
BASELINE_DD_PCT = 4.43

# V1 anchor metrics for reference (re-confirmed with patched simulator)
V1_PNL = 61_313.0
V1_DD = 3_074.0
V1_DD_PCT = 4.12


# ---------------------------------------------------------------------------
# B-COMBO BASELINE PARAMS — the new starting point
# ---------------------------------------------------------------------------
# This is V2 with the V1-compat translation PLUS the B combo overrides
# discovered in Phase 6 of the v1 campaign and confirmed as the new top
# by Phase 11 re-rank.
BASELINE_PARAMS = {
    # --- Core selectivity ---
    "long_prep_threshold":  3,
    "long_threshold":       5,
    "short_prep_threshold": 3,
    "short_threshold":      5,
    "min_gap":              9,

    # --- Candle filter — TIGHTENED to 0.3 (vs V1's 0.4) ---
    "max_candle_pct": 0.3,

    # --- Risk Management — B-combo's sl_max=60 (vs V1's 100) ---
    "sl_lookback":   5,
    "sl_max_points": 60.0,
    "rr_tp":         2.5,
    "tick_buffer":   0,
    "be_at_rr":      0.0,    # off — BE in v1 was misleadingly attractive due to DD bug

    # --- 1) Oscillator ---
    "osc_on":                 True,
    "hyper_wave_length":      5,
    "signal_type":            "SMA",
    "signal_length":          3,
    "mf_length":              35,
    "mf_smooth":              5,
    "hw_filter_on":           True,
    "hw_level":               16.0,
    "hw_extreme_filter_on":   True,
    "hw_extreme":             20.0,
    "sig_extreme_filter_on":  True,  # ENABLED in B combo
    "sig_extreme":            40.0,  # B combo's threshold
    "cloud_filter_on":        True,
    "delta_filter_on":        True,
    "cloud_zero_filter_on":   False,
    "delta_off_mode":         "both",
    "pts_hw_sens":            1,
    "pts_hw_value":           1,
    "pts_hw_extreme":         1,
    "pts_sig_extreme":        1,
    "pts_cloud":              1,
    "pts_delta":              1,
    "pts_cloud_zero":         0,

    # --- 2) Double EMA ---
    "ema_on":         True,
    "ema_prin_len":   30,
    "ema_sec_len":    20,
    "pts_ema_break":  1,
    "pts_ema_align":  1,

    # --- 3) Supertrend ---
    "st_on":   True,
    "st_atr":  14,
    "st_mult": 3.0,
    "pts_st":  1,

    # --- 4) Alligator ---
    "alligator_on":    True,
    "jaw_length":      13,
    "teeth_length":    8,
    "lips_length":     5,
    "jaw_offset":      8,
    "teeth_offset":    5,
    "lips_offset":     3,
    "pts_alligator":   1,
    "pts_alli_offset": 1,
    "pts_retest_lips": 1,

    # --- 5) UT Bot ---
    "ut_on":         True,
    "ut_key":        1.0,
    "ut_atr_period": 10,
    "pts_ut_bot":    1,

    # --- 6) STC ---
    "stc_on":        True,
    "stc_length":    12,
    "stc_fast_len":  26,
    "stc_slow_len":  50,
    "stc_min_long":  1.0,
    "stc_max_long":  99.0,
    "stc_min_short": 1.0,
    "stc_max_short": 99.0,
    "pts_stc":       1,

    # --- 7) HMA Ribbon + SSL ---
    "hma_on":          True,
    "hma_ema_len":     7,
    "hma1_len":        42,
    "hma2_len":        84,
    "amp_mult":        3.0,   # B combo (vs V1's 2.5)
    "hma_pol_bars":   -1,
    "ssl_len":         60,
    "ssl_mult":        0.2,
    "hma_window_bars": 0,
    "pts_hma_break":   1,
    "pts_hma_slow":    0,
}


def anchor_engine():
    """V1's blackout windows — reconfirmed optimal in v1 campaign Phase 8."""
    from backend.api import BacktestEngineSettings, BlackoutWindowSettings

    return BacktestEngineSettings(
        auto_close_enabled=True,
        auto_close_hour=22,
        auto_close_minute=0,
        blackout_windows=[
            BlackoutWindowSettings(active=True,  start_hour=9,  start_minute=0,  end_hour=10, end_minute=0),
            BlackoutWindowSettings(active=True,  start_hour=13, start_minute=0,  end_hour=14, end_minute=0),
            BlackoutWindowSettings(active=True,  start_hour=17, start_minute=0,  end_hour=23, end_minute=59),
            BlackoutWindowSettings(active=False, start_hour=15, start_minute=30, end_hour=15, end_minute=35),
            BlackoutWindowSettings(active=False, start_hour=16, start_minute=30, end_hour=22, end_minute=0),
            BlackoutWindowSettings(active=False, start_hour=21, start_minute=0,  end_hour=23, end_minute=59),
            BlackoutWindowSettings(active=False, start_hour=9,  start_minute=0,  end_hour=10, end_minute=0),
            BlackoutWindowSettings(active=False, start_hour=13, start_minute=0,  end_hour=14, end_minute=0),
            BlackoutWindowSettings(active=False, start_hour=17, start_minute=0,  end_hour=21, end_minute=0),
        ],
        debug=False,
        daily_win_limit_enabled=False,
        daily_win_limit=800.0,
        daily_loss_limit_enabled=False,
        daily_loss_limit=700.0,
        daily_limit_mode="after_close",
    )


def build_engine(active_windows):
    """Custom engine for blackout sweeps. `active_windows` is a list of
    tuples (start_h, start_m, end_h, end_m); the 22-23:59 close lock is
    always present."""
    from backend.api import BacktestEngineSettings, BlackoutWindowSettings

    blackouts = [
        BlackoutWindowSettings(
            active=True, start_hour=sh, start_minute=sm, end_hour=eh, end_minute=em
        )
        for sh, sm, eh, em in active_windows
    ]
    has_late = any(w.start_hour == 22 and w.end_hour == 23 for w in blackouts)
    if not has_late:
        blackouts.append(
            BlackoutWindowSettings(active=True, start_hour=22, start_minute=0,
                                   end_hour=23, end_minute=59)
        )
    return BacktestEngineSettings(
        auto_close_enabled=True,
        auto_close_hour=22,
        auto_close_minute=0,
        blackout_windows=blackouts,
        debug=False,
        daily_win_limit_enabled=False,
        daily_win_limit=800.0,
        daily_loss_limit_enabled=False,
        daily_loss_limit=700.0,
        daily_limit_mode="after_close",
    )
