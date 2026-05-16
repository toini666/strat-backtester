"""Verify the winner preset reproduces expected metrics.

Edit EXPECTED with the final winning metrics after sweep 08.
"""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from scripts.goals._shared.preset import verify_preset  # noqa: E402


EXPECTED = {
    "net_pnl": 35_472.0,
    "max_dd_$": 2_491.0,
    "trades": 1405,
    "win_rate": 43.8,
    "profit_factor": 1.41,
}


if __name__ == "__main__":
    preset_path = Path(__file__).resolve().parent / "winner_preset.json"
    ok = verify_preset(preset_path, EXPECTED)
    sys.exit(0 if ok else 1)
