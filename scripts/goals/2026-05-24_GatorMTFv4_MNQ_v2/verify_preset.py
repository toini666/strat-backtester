"""Verify the v2 winner preset replays to its stored metrics."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from scripts.goals._shared.preset import verify_preset


WINNER_PRESET = Path(__file__).resolve().parent / "winner_preset.json"

EXPECTED = {
    "net_pnl": 16776.88,
    "max_dd_$": 2161.6,
    "trades": 2316,
    "win_rate": 44.0,
    "profit_factor": 1.13,
}


def main():
    ok = verify_preset(WINNER_PRESET, EXPECTED, pnl_tolerance=10.0, dd_tolerance=10.0)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
