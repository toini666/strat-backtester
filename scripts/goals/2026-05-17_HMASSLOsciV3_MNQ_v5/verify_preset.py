"""Verify the V5 winner preset reproduces the expected metrics.

Run:  python scripts/goals/2026-05-17_HMASSLOsciV3_MNQ_v5/verify_preset.py
"""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from scripts.goals._shared.preset import verify_preset

EXPECTED = {
    "net_pnl": 68_765,
    "max_dd_$": 1_579,
    "trades": 1_241,
    "win_rate": 48.3,
    "profit_factor": 1.70,
}

if __name__ == "__main__":
    ok = verify_preset(
        Path(__file__).resolve().parent / "winner_preset.json",
        EXPECTED,
        pnl_tolerance=50.0,
        dd_tolerance=50.0,
    )
    sys.exit(0 if ok else 1)
