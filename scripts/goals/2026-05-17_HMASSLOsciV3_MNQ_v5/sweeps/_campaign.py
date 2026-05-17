"""Campaign-local constants — HMASSLOsciV3 / MNQ v5 — 2025-01-06 → 2026-05-15 (~17 mo).

Goal:
- Starting point: V4 winner (ema=11, BO 11+14, r=0.0036) = $50,770 PnL / $2,268 DD / Ratio 22.39.
- Maximize PnL subject to **MaxDD < $2,000** (HARD cap — tighter than V4's $2,500).
- Budget: 200 simulations.

Approach (per analysis report 2026-05-17):
- Stop-loss is the only source of structural loss (-$273k across 3 winners).
- 187 trades ≤1 bar = -$26k (intra-bar fakeouts). Levers: tighter max_candle_pct + max_sl_points.
- V4 never tested daily_limits — open lever.
- DOW analysis: Mon/Wed/Thu 3-4x less profitable than Tue/Fri — DOW blackout opportunity.
- Effective DD target = $1,950 (safety margin under $2,000).

Key invariants:
- auto_close_hour = 22, auto_close_minute = 0 (CME daily close — FIXED)
- Daily-limits tested intra_bar first, after_close fallback.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

STRATEGY = "HMASSLOsciV3"
SYMBOL = "MNQ"
TF = "7m"
START = "2025-01-06T00:00"
END = "2026-05-15T00:00"
INITIAL_EQUITY = 50_000.0
MAX_CONTRACTS = 50

DEFAULT_RISK = 0.0036  # V4 winner risk

TARGET_PNL_MIN = 50_000.0       # do not regress vs V4 if possible
TARGET_MAX_DD = 2_000.0         # HARD cap — mission requirement
SAFE_MAX_DD = 1_950.0           # effective target (replay variance margin)

# V4 winner overrides — seed of this campaign.
V4_WINNER_PARAMS = {
    "ema_len": 11,                 # V4 breakthrough
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
    "mf_length": 25,
    "mf_smooth": 6,
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

# V4 winner blackouts (in addition to UI default 22:00-23:59)
V4_EXTRA_BLACKOUTS = [
    {"start_hour": 11, "start_minute": 0, "end_hour": 12, "end_minute": 0},
    {"start_hour": 14, "start_minute": 0, "end_hour": 15, "end_minute": 0},
]


def window(start_h, end_h, start_m=0, end_m=0):
    """Helper: build an active-blackout dict for make_engine_settings."""
    return {"start_hour": start_h, "start_minute": start_m,
            "end_hour": end_h, "end_minute": end_m}
