"""Verify the winner_preset.json replays to the expected metrics."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from scripts.goals._shared.preset import verify_preset  # noqa: E402

CAMPAIGN_DIR = Path(__file__).resolve().parent
PRESET_PATH = CAMPAIGN_DIR / "winner_preset.json"

EXPECTED = {
    "net_pnl": 80398.42,
    "max_dd_$": 2493.02,
    "trades": 828,
    "win_rate": 39.6,
    "profit_factor": 1.58,
}


def main() -> int:
    ok = verify_preset(PRESET_PATH, EXPECTED, pnl_tolerance=50.0, dd_tolerance=50.0)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
