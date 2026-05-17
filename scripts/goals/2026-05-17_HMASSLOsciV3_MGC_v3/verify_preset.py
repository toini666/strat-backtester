"""Verify the V3 winner preset replays to expected metrics."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from scripts.goals._shared.preset import verify_preset  # noqa: E402

EXPECTED = {
    "net_pnl": 44_692.0,
    "max_dd_$": 1_944.0,
    "trades": 865,
    "win_rate": 55.1,
    "profit_factor": 1.66,
}

if __name__ == "__main__":
    ok = verify_preset(Path(__file__).resolve().parent / "winner_preset.json", EXPECTED)
    sys.exit(0 if ok else 1)
