"""Campaign-local constants — HMASSLOsciV3 / MGC — 2025-01-06 → 2026-05-15.

Goal:
- Net PnL > $30,000
- Max DD  < $2,500

Key invariants for any final config:
- auto_close_hour = 22, auto_close_minute = 0 (CME daily close — reference Brussels)
- Daily limits stay DISABLED for this campaign (per user instruction). We do not
  sweep daily_win_limit / daily_loss_limit; both flags remain off in every config.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

STRATEGY = "HMASSLOsciV3"
SYMBOL = "MGC"
START = "2025-01-06T00:00"
END = "2026-05-15T00:00"
INITIAL_EQUITY = 50_000.0
MAX_CONTRACTS = 50
DEFAULT_RISK = 0.01

TFS_PRIORITY = ["3m", "5m", "7m", "10m"]
TFS_EXTRA = ["2m", "15m"]
ALL_TFS = TFS_PRIORITY + TFS_EXTRA

TARGET_PNL = 30_000.0
TARGET_MAX_DD = 2_500.0
