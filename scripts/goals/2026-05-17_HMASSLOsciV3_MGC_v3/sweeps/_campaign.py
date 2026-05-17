"""Campaign-local constants for HMASSLOsciV3 / MGC v3.

Starting point: V2 winner (PnL=$44,711 / DD=$2,378 / ratio 18.80).
Goal V3: reduce DD < $2,000 while maximizing PnL (budget 200 sims).

Reference: scripts/goals/2026-05-16_HMASSLOsciV3_MGC_v2/winner_preset.json
"""

from __future__ import annotations

STRATEGY = "HMASSLOsciV3"
SYMBOL = "MGC"
INTERVAL = "7m"
START = "2025-01-06T00:00"
END = "2026-05-15T00:00"
INITIAL_EQUITY = 50_000.0
MAX_CONTRACTS = 50

# V2 winner overrides on top of HMASSLOsciV3 default_params
V2_WINNER_OVERRIDES = {
    "hma1_len": 9,                              # default 13
    "hma2_len": 34,                             # default 21
    "hw_range_on": True,                        # default False
    "block_loss_exit_before_partial": True,     # default False
    "max_sl_points": 100.0,                     # default 300.0
    "tick_buffer": 1,                           # default 0
}
V2_WINNER_RISK = 0.0047

# V2 winner blackouts (in addition to UI default 22-23:59).
# Format: (start_h, start_m, end_h, end_m)
V2_WINNER_BLACKOUTS = [
    (3, 0, 4, 0),
    (6, 0, 7, 0),
    (7, 0, 8, 0),
    (9, 0, 10, 0),
    (11, 0, 12, 0),
]

GOAL_PNL = 44_711.0   # V2 winner PnL — try to beat
GOAL_DD = 2_000.0     # New ceiling (V2 was 2,378)

# Budget bookkeeping (approx).
# Update each sweep header with running total.
BUDGET = 200


def pdd(net_pnl: float, dd_dollars: float) -> float:
    if dd_dollars <= 0:
        return float("inf")
    return net_pnl / dd_dollars
