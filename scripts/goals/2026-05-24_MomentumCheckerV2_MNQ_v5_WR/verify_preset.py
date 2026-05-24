"""Verify the winner preset by replaying it and matching to expected metrics."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from scripts.goals._shared.preset import verify_preset


PRESET = Path(__file__).parent / "winner_preset.json"
EXPECTED = {
    "net_pnl": 69571.0,
    "max_dd_$": 2367.0,
    "trades": 608,
    "win_rate": 52.6,
    "profit_factor": 1.66,
}


if __name__ == "__main__":
    ok = verify_preset(PRESET, EXPECTED, pnl_tolerance=100.0, dd_tolerance=100.0)
    sys.exit(0 if ok else 1)
