"""Replay winner_preset.json and confirm metrics match expected.

Expected (from sweep 10):
  PnL=$80,709 / DD=$3,236 / 1299 trades / WR=48.7% / PF=1.64
"""

from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "sweeps"))
sys.path.insert(0, str(HERE.parent))  # scripts/goals

# Import harness FIRST — it inserts the repo root into sys.path so that
# backend.api becomes importable for the preset module.
from _shared.harness import run_backtest  # noqa: F401, E402
from _shared.preset import verify_preset  # noqa: E402


if __name__ == "__main__":
    expected = {
        "net_pnl": 80709.42,
        "max_dd_$": 3235.78,
        "trades": 1299,
        "win_rate": 48.7,
        "profit_factor": 1.64,
    }
    ok = verify_preset(
        HERE / "winner_preset.json",
        expected,
        pnl_tolerance=50.0,
        dd_tolerance=50.0,
    )
    sys.exit(0 if ok else 1)
