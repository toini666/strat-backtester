"""Verify the V4 winner preset reproduces the expected metrics.

Run:  python scripts/goals/2026-05-19_HMASSLOsciV4_MNQ/verify_preset.py
"""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from scripts.goals._shared.preset import verify_preset

# Canonical replay metrics (what the UI reproduces when loading the preset).
# The direct optimisation call returned $75,289 / 1,173 trades; the preset
# replay returns $75,236 / 1,175 trades. The $53 drift comes from float-
# precision when riskPerTrade roundtrips through 100x→/100. The replay
# numbers are what the user actually sees in the UI — those are canonical.
EXPECTED = {
    "net_pnl": 75_236,
    "max_dd_$": 1_911,
    "trades": 1175,
    "win_rate": 49.4,
    "profit_factor": 1.82,
}

if __name__ == "__main__":
    ok = verify_preset(
        Path(__file__).resolve().parent / "winner_preset.json",
        EXPECTED,
        pnl_tolerance=5.0,
        dd_tolerance=5.0,
    )
    sys.exit(0 if ok else 1)
