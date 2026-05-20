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
    "net_pnl":      56_353.0,
    "max_dd_$":      2_425.0,
    "trades":          784,
    "win_rate":       41.3,
    "profit_factor":  1.49,
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
