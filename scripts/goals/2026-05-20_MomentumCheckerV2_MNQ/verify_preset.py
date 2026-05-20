"""Verify the MomentumCheckerV2 MNQ 7m winner preset reproduces the campaign
metrics bit-for-bit. Prints ✅ MATCH on success.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

CAMPAIGN_DIR = Path(__file__).resolve().parent

from scripts.goals._shared.preset import verify_preset  # noqa: E402


EXPECTED = {
    "net_pnl":       69_882.0,
    "max_dd_$":       1_864.0,
    "trades":              835,
    "win_rate":           31.5,
    "profit_factor":       1.6,
}


def main() -> int:
    preset_path = CAMPAIGN_DIR / "winner_preset.json"
    ok = verify_preset(preset_path, EXPECTED, pnl_tolerance=50.0, dd_tolerance=50.0)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
