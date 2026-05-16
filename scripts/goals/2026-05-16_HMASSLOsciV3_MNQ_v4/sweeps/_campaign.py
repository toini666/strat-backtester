"""Campaign-local constants — HMASSLOsciV3 / MNQ v4 — 2025-01-06 → 2026-05-15 (~17 mo).

Goal:
- Starting point: v3 winner (cd=3, sx=40, r=0.0032) = $35.5k PnL / $2.49k DD / Ratio 14.24.
- Maximize PnL subject to MaxDD < $2,500.
- Budget: 250 simulations.

Approach (per advisor briefing):
- Blackouts are the highest-leverage unused lever (v3 forbade them, this campaign re-opens them).
- v3 hour diagnostic showed ~$8.6k toxic PnL across H=14/06/12/08/11.
- Each $200-300 DD reduction can be re-invested as risk_per_trade for higher PnL.

Key invariants:
- auto_close_hour = 22, auto_close_minute = 0 (CME daily close)
- Effective DD target = $2,400 (safety margin under $2,500)
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

DEFAULT_RISK = 0.0032

TARGET_PNL_MIN = 35_000.0
TARGET_PNL_GOAL = 40_000.0
TARGET_MAX_DD = 2_500.0
SAFE_MAX_DD = 2_400.0  # effective target (replay variance margin)

# v3 winner overrides — seed of this campaign.
V3_WINNER_PARAMS = {
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
    "hw_dir_on": False,           # v3 sweep 02
    "hw_extreme_on": True,
    "hw_extreme": 20.0,
    "sig_extreme_on": True,
    "sig_extreme": 40,             # v3 sweep 03b
    "hw_range_on": False,
    "hw_range": 10.0,
    "cloud_on": True,
    "delta_on": True,
    "cloud_zero_on": False,
    "delta_ext_on": False,
    "tick_buffer": 0,
    "max_sl_points": 300.0,
    "cooldown_bars": 3,            # v3 sweep 03b breakthrough
    "max_candle_pct": 0.9,
    "signal_candle_sl_on": False,
    "one_trade_per_entry_window": True,
    "hw_partial_pct": 0.0,
    "hw_partial_min_rr": 0.0,
    "block_loss_exit_before_partial": False,
    "final_exit_mode": "HMA rapide/SSL → HW",
    "final_exit_pct": 0.1,
}
