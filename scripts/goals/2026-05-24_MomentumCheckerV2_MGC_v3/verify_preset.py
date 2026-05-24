"""Verify the 3 v3 presets replay to their stored metrics.

Run:
    python scripts/goals/2026-05-24_MomentumCheckerV2_MGC_v3/verify_preset.py

Must print ✅ MATCH for each preset.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from scripts.goals._shared.preset import verify_preset


CAMPAIGN = Path(__file__).resolve().parent

PRESETS = ["winner_preset.json", "alt_highpnl_preset.json", "alt_wr_preset.json"]


def main() -> None:
    all_ok = True
    for fname in PRESETS:
        path = CAMPAIGN / fname
        preset = json.loads(path.read_text())
        expected = {
            "net_pnl": preset["metrics"]["total_return"] * preset["initialEquity"] / 100,
            "max_dd_$": preset["metrics"].get("max_drawdown_dollars", 0),
            "trades": preset["metrics"]["total_trades"],
            "win_rate": round(preset["metrics"]["win_rate"], 1),
            "profit_factor": None,
        }
        print(f"\n=== Verifying {fname} ({preset['name']}) ===")
        ok = verify_preset(path, expected, pnl_tolerance=10.0, dd_tolerance=10.0)
        all_ok = all_ok and ok

    print("\n" + ("✅ ALL MATCH" if all_ok else "❌ SOME PRESETS FAIL"))
    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
