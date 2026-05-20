"""Verify the winner preset replays to the expected metrics.

Uses the shared `verify_preset` helper, which loads the preset, runs the
backtest exactly the way the UI would, and prints ✅ MATCH if metrics align.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from scripts.goals._shared.preset import verify_preset  # noqa: E402


CAMPAIGN_DIR = Path(__file__).resolve().parent
PRESET = CAMPAIGN_DIR / "winner_preset.json"


EXPECTED = {
    "net_pnl": 58_249,
    "max_dd_$": 2_486,
    "trades": 851,
    "win_rate": 39.7,
    "profit_factor": 1.54,
}


def main() -> int:
    if not PRESET.exists():
        print(f"❌ Preset file not found: {PRESET}")
        return 1
    ok = verify_preset(PRESET, EXPECTED, pnl_tolerance=100.0, dd_tolerance=100.0)
    return 0 if ok else 2


if __name__ == "__main__":
    sys.exit(main())
