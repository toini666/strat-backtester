"""Campaign-local constants — HMASSLOsciV3 / MNQ — 2025-01-06 → 2026-05-13 (full ~17 months).

Goal:
- Net PnL > $30,000
- Max DD  < $2,500

Key invariants for any final config:
- auto_close_hour = 22, auto_close_minute = 0 (CME daily close)
- Daily-limits first tested in "intra_bar", fallback "after_close".
"""

from __future__ import annotations

import sys
from pathlib import Path

# Make `scripts.goals._shared` importable from any sweep script.
ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

STRATEGY = "HMASSLOsciV3"
SYMBOL = "MNQ"
START = "2025-01-06T00:00"
END = "2026-05-13T18:39"
INITIAL_EQUITY = 50_000.0
MAX_CONTRACTS = 50
DEFAULT_RISK = 0.01  # 1 % — baseline. Final winner risk decided by sweeps.

TFS_PRIORITY = ["3m", "5m", "7m", "10m"]
TFS_EXTRA = ["2m", "15m"]
ALL_TFS = TFS_PRIORITY + TFS_EXTRA

TARGET_PNL = 30_000.0
TARGET_MAX_DD = 2_500.0
