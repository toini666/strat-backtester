"""Verify the v5 PnL winner preset replays cleanly. Must print ✅ MATCH."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from scripts.goals._shared.preset import verify_preset  # noqa: E402


def main() -> None:
    here = Path(__file__).resolve().parent
    expected = json.loads((here / "expected_winner_metrics.json").read_text())
    ok = verify_preset(here / "winner_preset.json", expected,
                       pnl_tolerance=5.0, dd_tolerance=5.0)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
