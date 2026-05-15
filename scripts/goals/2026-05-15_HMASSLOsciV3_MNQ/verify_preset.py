"""Verify the winning preset for HMASSLOsciV3 / MNQ reproduces the reported numbers."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from scripts.goals._shared.preset import verify_preset

HERE = Path(__file__).resolve().parent
PRESET = HERE / "winner_preset.json"

EXPECTED = {
    "net_pnl": 33_699,
    "max_dd_$": 2_319,
    "trades": 368,
    "win_rate": 45.9,
    "profit_factor": 1.78,
}


if __name__ == "__main__":
    ok = verify_preset(PRESET, EXPECTED)
    sys.exit(0 if ok else 1)
