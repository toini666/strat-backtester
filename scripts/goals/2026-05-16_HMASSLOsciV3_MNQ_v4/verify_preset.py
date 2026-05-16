"""Verify the winner preset reproduces expected metrics."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from scripts.goals._shared.preset import verify_preset  # noqa: E402


EXPECTED = {
    "net_pnl": 50_770.0,
    "max_dd_$": 2_268.0,
    "trades": 1389,
    "win_rate": 46.1,
    "profit_factor": 1.58,
}


if __name__ == "__main__":
    preset_path = Path(__file__).resolve().parent / "winner_preset.json"
    ok = verify_preset(preset_path, EXPECTED)
    sys.exit(0 if ok else 1)
