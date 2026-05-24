"""Verify the WINNER preset reproduces — must print ✅ MATCH."""
from __future__ import annotations
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from scripts.goals._shared.preset import verify_preset


def main():
    here = Path(__file__).resolve().parent
    preset_path = here / "winner_preset.json"
    expected_path = here / "expected_winner_metrics.json"

    if not preset_path.exists():
        print(f"❌ Preset file not found: {preset_path}")
        sys.exit(1)
    if not expected_path.exists():
        print(f"❌ Expected metrics not found: {expected_path}")
        sys.exit(1)

    expected = json.loads(expected_path.read_text())
    print(f"--- Verifying {preset_path.name} ---")
    ok = verify_preset(preset_path, expected, pnl_tolerance=10.0, dd_tolerance=10.0)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
