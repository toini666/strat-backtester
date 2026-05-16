"""Verify the winner preset reproduces the campaign's headline metrics.

Run: python scripts/goals/2026-05-16_HMASSLOsciV2_MGC/verify_preset.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from scripts.goals._shared.preset import verify_preset  # noqa: E402


EXPECTED = {
    "net_pnl": 44006.4,
    "max_dd_$": 6587.56,
    "trades": 795,
    "win_rate": 53.5,
    "profit_factor": 1.31,
}


if __name__ == "__main__":
    ok = verify_preset(
        Path(__file__).resolve().parent / "winner_preset.json",
        EXPECTED,
    )
    sys.exit(0 if ok else 1)
