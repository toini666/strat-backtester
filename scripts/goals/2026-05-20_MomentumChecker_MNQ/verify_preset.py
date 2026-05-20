"""Replay winner_preset.json and verify the metrics match exactly.

Must print ✅ MATCH for the campaign to be considered complete.
"""

from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))

from scripts.goals._shared.preset import verify_preset


EXPECTED = {
    "net_pnl":      62_262.0,
    "max_dd_$":      2_431.0,
    "trades":          764,
    "win_rate":       40.1,
    "profit_factor":  1.53,
}


def main() -> int:
    ok = verify_preset(
        preset_path=HERE / "winner_preset.json",
        expected=EXPECTED,
        pnl_tolerance=50.0,
        dd_tolerance=50.0,
    )
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
