"""Campaign-local constants for MNQ GatorMTFv4 v1 PnL-focused campaign.

Goal: maximise PnL with max DD ≤ $2,500. Budget = 1000 simulations.

Baseline preset 'GatorMTFv4 - MNQ 1m':
  PnL = -$25,532 / DD = $20,419 / N = 3,773 / WR = 50.25 %.

The DD is ~8× over budget at the seed, so the campaign will need
heavy cuts via strategy params (cases, cooldown, RR, filters) and
blackouts before we can dial risk back up safely.

User constraints (immutable):
  - symbol MNQ
  - interval 1m
  - max contracts 20
  - daily win/loss limits OFF
  - use full available data
"""

from __future__ import annotations

# Period — full available MNQ 1m history (data: 2025-01-02 → 2026-05-22)
# Note: previous default was 2025-01-08 to match the seed preset, but the
# user requirement is to use ALL available data. Use the dataset start.
START = "2025-01-02T00:00"
END   = "2026-05-22T22:59"

SYMBOL   = "MNQ"
INTERVAL = "1m"
STRATEGY = "GatorMTFv4"

INITIAL_EQUITY = 50_000.0
MAX_CONTRACTS  = 20

# Seed risk from the user's preset.
SEED_RISK = 0.5 / 100   # 0.5 %

# Seed params — copy of the preset.
SEED_PARAMS = {
    "trigger_tf_minutes": 7,
    "ema_len": 7,
    "hma1_len": 13,
    "hma2_len": 21,
    "amp_mult": 2.0,
    "entry_window_bars_trigger": 5,
    "ssl_len": 60,
    "ssl_mult": 0.2,
    "hyper_wave_length": 5,
    "signal_length": 3,
    "mf_length": 35,
    "mf_smooth": 6,
    "sig_extreme_threshold": 20.0,
    "case_a_on": True,
    "case_b_on": True,
    "case_c_on": True,
    "case_d_on": True,
    "sl_lookback": 1,
    "sl_min_pct": 0.15,
    "tick_buffer": 2,
    "cooldown_bars": 7,
    "hw_partial_pct": 0.0,
    "partial_rr": 0.0,
    "final_rr": 1.0,
    "one_trade_per_window": True,
}

# Seed engine settings — match the preset (only 22:00–23:59 active).
SEED_AUTO_CLOSE = (22, 0)
SEED_BLACKOUTS = [
    (22, 0, 23, 59),
]

GOAL_DD = 2500.0
