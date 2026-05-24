"""Verify the WINNER preset replays to the expected metrics."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from scripts.goals._shared.preset import verify_preset

EXPECTED = {
    "net_pnl": 88_430,
    "max_dd_$": 2_341,
    "trades": 765,
    "win_rate": 41.8,
    "profit_factor": 1.72,
}

if __name__ == "__main__":
    ok = verify_preset(
        Path(__file__).resolve().parent / "winner_preset.json",
        EXPECTED,
        pnl_tolerance=50.0,
        dd_tolerance=50.0,
    )
    sys.exit(0 if ok else 1)
