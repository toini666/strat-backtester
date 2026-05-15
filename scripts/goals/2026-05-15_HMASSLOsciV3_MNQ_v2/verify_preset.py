"""Replay winner_preset.json and verify metrics match expected values."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from scripts.goals._shared.preset import verify_preset  # noqa: E402

EXPECTED = {
    "net_pnl": 30_401.96,
    "max_dd_$": 1_960.06,
    "trades": 998,
    "win_rate": 47.5,
    "profit_factor": 1.51,
}

if __name__ == "__main__":
    ok = verify_preset(Path(__file__).resolve().parent / "winner_preset.json",
                       EXPECTED, pnl_tolerance=50.0, dd_tolerance=50.0)
    sys.exit(0 if ok else 1)
