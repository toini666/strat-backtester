"""Verification script — replays winner_preset.json and asserts metrics match."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from scripts.goals._shared.preset import verify_preset


EXPECTED = {
    "net_pnl": 44_711,
    "max_dd_$": 2_378,
    "trades": 1142,
    "win_rate": 55.9,
    "profit_factor": 1.56,
}


if __name__ == "__main__":
    ok = verify_preset(Path(__file__).resolve().parent / "winner_preset.json", EXPECTED)
    sys.exit(0 if ok else 1)
