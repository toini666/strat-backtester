"""Campaign-local constants for HMASSLOsciV3 / MGC v2.

Starting point = winner preset from the first MGC campaign
(scripts/goals/2026-05-15_HMASSLOsciV3_MGC/winner_preset.json) BUT with
all blackouts removed except the default 22:00-23:59 (UI default for
HMASSLOsciV3). Goal: re-optimize strategy params to push beyond
P/DD = 10.16 and reach PnL > 30k$ AND DD < 2.5k$ simultaneously.
"""

from __future__ import annotations

STRATEGY = "HMASSLOsciV3"
SYMBOL = "MGC"
INTERVAL = "7m"
START = "2025-01-06T00:00"
END = "2026-05-15T00:00"
INITIAL_EQUITY = 50_000.0
MAX_CONTRACTS = 50

# Winner from previous MGC campaign — overrides on top of v3 default_params.
# Reproduces PnL=32,821 / DD=3,230 with the 3 extra blackouts; we want to
# re-explore the param space WITHOUT those 3 extras (only 22-23:59 active).
PREV_WINNER_OVERRIDES = {
    "hma2_len": 34,
    "hw_range_on": True,
}
PREV_WINNER_RISK = 0.0052

GOAL_PNL = 30_000.0
GOAL_DD = 2_500.0


def pdd(net_pnl: float, dd_dollars: float) -> float:
    if dd_dollars <= 0:
        return float("inf")
    return net_pnl / dd_dollars
