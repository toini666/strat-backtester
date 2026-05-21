"""Verify the v2 MGC winner preset replays to expected metrics.

Prints ✅ MATCH for each preset that reproduces within $50.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from scripts.goals._shared.preset import verify_preset  # noqa: E402

CAMPAIGN_DIR = Path(__file__).resolve().parent


def main() -> int:
    print("=" * 90)
    print("VERIFY — v2 MGC MomentumCheckerV2 presets")
    print("=" * 90)
    all_match = True

    print("\n--- WINNER ---")
    ok = verify_preset(
        CAMPAIGN_DIR / "winner_preset.json",
        expected={
            "net_pnl": 58_625.0,
            "max_dd_$": 2_434.0,
            "trades": 810,
            "win_rate": 39.6,
            "profit_factor": 1.58,
        },
    )
    all_match = all_match and ok

    print("\n--- ALT_ROBUST ---")
    ok = verify_preset(
        CAMPAIGN_DIR / "alt_robust_preset.json",
        expected={
            "net_pnl": 56_275.0,
            "max_dd_$": 2_135.0,
            "trades": 810,
            "win_rate": 39.6,
            "profit_factor": 1.57,
        },
    )
    all_match = all_match and ok

    print("\n--- ALT_MINDD ---")
    ok = verify_preset(
        CAMPAIGN_DIR / "alt_mindd_preset.json",
        expected={
            "net_pnl": 55_054.0,
            "max_dd_$": 2_117.0,
            "trades": 812,
            "win_rate": 39.5,
            "profit_factor": 1.56,
        },
    )
    all_match = all_match and ok

    print("\n" + "=" * 90)
    print("Overall:", "✅ ALL MATCH" if all_match else "❌ AT LEAST ONE MISMATCH")
    return 0 if all_match else 1


if __name__ == "__main__":
    sys.exit(main())
