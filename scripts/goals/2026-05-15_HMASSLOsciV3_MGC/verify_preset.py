"""Verify the winner preset reproduces the campaign's headline metrics.

Run: python scripts/goals/2026-05-15_HMASSLOsciV3_MGC/verify_preset.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from scripts.goals._shared.preset import verify_preset  # noqa: E402


# Filled in once the final winner has been validated by sweep 08.
EXPECTED = {
    "net_pnl": 32821.40,
    "max_dd_$": 3230.12,
    "trades": 1319,
    "win_rate": 46.3,
    "profit_factor": 1.30,
}


if __name__ == "__main__":
    ok = verify_preset(
        Path(__file__).resolve().parent / "winner_preset.json",
        EXPECTED,
    )
    sys.exit(0 if ok else 1)
