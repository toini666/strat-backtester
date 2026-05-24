"""Campaign-local constants for MNQ GatorMTFv4 v2 PnL-maximisation campaign.

Goal: PnL ≥ $50,000 with max_dd_$ ≤ $2,500 — i.e. **20× DD-adjusted ratio**.

v1 outcome: PnL +$13,130 / DD $2,461 (5.34× ratio) — PF = 1.17.
v2 needs ~3.7× the ratio. This is structurally a PF problem — raising risk
linearly raised DD faster than PnL (sweep 6 of v1: risk 1.0 % → PF same,
PnL=$60k but DD=$13k, ratio 4.6× — WORSE than 0.26 %).

Strategy: explore the structural levers v1 left on the table:
  - trigger_tf_minutes (kept at 7)
  - HMA stack (ema_len, hma1_len, hma2_len) untouched
  - amp_mult (only spot-checked 1.0 vs 2.0)
  - ssl_len / ssl_mult (untouched)
  - final_rr capped at 2.0 (try 2.5, 3, 4, 5)
  - case bitmask: only 1101 tested vs 1111 — minimal combos (1000, 0100…)
  - SL geometry combo with RR (memory: feedback_sl_lookback_rr_interaction)

User constraints (immutable):
  - symbol MNQ
  - interval 1m
  - max contracts 20
  - daily win/loss limits OFF (confirmed for v2 too)
  - use full available data
  - auto_close = 22:00
"""

from __future__ import annotations

START = "2025-01-02T00:00"
END   = "2026-05-22T22:59"

SYMBOL   = "MNQ"
INTERVAL = "1m"
STRATEGY = "GatorMTFv4"

INITIAL_EQUITY = 50_000.0
MAX_CONTRACTS  = 20

# Sweep risk — use 0.5% during structural sweeps for stronger PnL signal.
# Final risk is tuned in Phase 8 to fit the DD budget.
SWEEP_RISK = 0.5 / 100

# v1 winner params (the baseline we're trying to beat structurally).
V1_WINNER_PARAMS = {
    "trigger_tf_minutes": 7,
    "ema_len": 7,
    "hma1_len": 13,
    "hma2_len": 21,
    "amp_mult": 1.0,
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
    "case_c_on": False,   # v1 winner had C off
    "case_d_on": True,
    "sl_lookback": 1,
    "sl_min_pct": 0.15,
    "tick_buffer": 2,
    "cooldown_bars": 90,
    "hw_partial_pct": 0.0,
    "partial_rr": 0.0,
    "final_rr": 2.0,
    "one_trade_per_window": True,
}

# v1 winner blackout schedule.
V1_WINNER_BLACKOUTS = [
    (6, 0, 7, 0),
    (11, 0, 12, 0),
    (12, 0, 13, 0),
    (14, 0, 15, 0),
    (16, 0, 17, 0),
    (17, 0, 18, 0),
    (19, 0, 20, 0),
    (21, 0, 22, 0),
    (22, 0, 23, 59),
    (23, 0, 23, 59),
]

V1_WINNER_RISK = 0.26 / 100

# Auto-close (immutable for final config).
AUTO_CLOSE = (22, 0)

GOAL_DD = 2500.0
GOAL_PNL = 50_000.0
