"""Campaign-local constants — HMASSLOsciV3 / MNQ v3 — 2025-01-06 → 2026-05-15 (~17 mo).

Goal:
- Improve previous winner (PnL $30.4k / DD $2.0k with 7 active blackouts).
- Constraint: keep ONLY the 22:00-23:59 blackout active (UI default for HMASSLOsciV3).
- Net PnL > $35,000 (ideally > $40,000)
- Max DD  < $2,500

Key invariants for any final config:
- auto_close_hour = 22, auto_close_minute = 0 (CME daily close)
- Active blackouts: only 22:00-23:59 (no time-of-day filters added)
- Daily-limits first tested in "intra_bar", fallback "after_close".
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

STRATEGY = "HMASSLOsciV3"
SYMBOL = "MNQ"
START = "2025-01-06T00:00"
END = "2026-05-15T00:00"
INITIAL_EQUITY = 50_000.0
MAX_CONTRACTS = 50

# Baseline risk — final winner risk decided by sweeps.
DEFAULT_RISK = 0.0034

# Timeframes — 7m priority, 10m alternative (per goal file).
TFS_PRIORITY = ["7m", "10m"]
TFS_EXTRA = ["3m", "5m"]
ALL_TFS = TFS_PRIORITY + TFS_EXTRA

TARGET_PNL_MIN = 35_000.0
TARGET_PNL_GOAL = 40_000.0
TARGET_MAX_DD = 2_500.0

# Previous winner overrides (from 2026-05-15_HMASSLOsciV3_MNQ_v2/winner_preset.json),
# used as our starting point (we drop all the time-of-day blackouts from that preset).
PREV_WINNER_PARAMS = {
    "ema_len": 13,
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
    "hw_dir_on": True,
    "hw_extreme_on": True,
    "hw_extreme": 20.0,
    "sig_extreme_on": True,
    "sig_extreme": 30,
    "hw_range_on": False,
    "hw_range": 10.0,
    "cloud_on": True,
    "delta_on": True,
    "cloud_zero_on": False,
    "delta_ext_on": False,
    "tick_buffer": 0,
    "max_sl_points": 300.0,
    "cooldown_bars": 1,
    "max_candle_pct": 0.9,
    "signal_candle_sl_on": False,
    "one_trade_per_entry_window": True,
    "hw_partial_pct": 0.0,
    "hw_partial_min_rr": 0.0,
    "block_loss_exit_before_partial": False,
    "final_exit_mode": "HMA rapide/SSL → HW",
    "final_exit_pct": 0.1,
}
