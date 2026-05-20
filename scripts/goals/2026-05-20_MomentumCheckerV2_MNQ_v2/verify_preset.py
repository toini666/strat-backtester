"""Verify the v2 winner preset reproduces the campaign metrics."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

CAMPAIGN_DIR = Path(__file__).resolve().parent

from scripts.goals._shared.preset import verify_preset  # noqa: E402


EXPECTED = {
    "net_pnl":       80_565.0,
    "max_dd_$":       3_023.0,
    "trades":              797,
    "win_rate":           40.4,
    "profit_factor":      1.58,
}


def main() -> int:
    ok = verify_preset(
        preset_path=CAMPAIGN_DIR / "winner_preset.json",
        expected=EXPECTED,
        pnl_tolerance=50.0,
        dd_tolerance=50.0,
    )
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
