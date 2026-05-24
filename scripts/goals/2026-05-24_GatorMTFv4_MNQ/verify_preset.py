"""Verify the winner preset by replaying it and matching to expected metrics."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from scripts.goals._shared.preset import verify_preset


PRESET = Path(__file__).parent / "winner_preset.json"
EXPECTED = {
    "net_pnl": 13130.0,
    "max_dd_$": 2461.0,
    "trades": 1439,
    "win_rate": 37.8,
    "profit_factor": 1.17,
}


if __name__ == "__main__":
    ok = verify_preset(PRESET, EXPECTED, pnl_tolerance=50.0, dd_tolerance=50.0)
    sys.exit(0 if ok else 1)
