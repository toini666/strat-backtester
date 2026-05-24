"""Compact sweep helpers — call run_backtest + summarize + print in one line."""
from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import Any, Dict

ROOT = Path(__file__).resolve().parents[4]
CAMPAIGN = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(CAMPAIGN) not in sys.path:
    sys.path.insert(0, str(CAMPAIGN))

from scripts.goals._shared.harness import run_backtest, summarize, fmt_summary
from sweeps._campaign import seed_kwargs


def bench(label: str, **overrides) -> Dict[str, Any]:
    t0 = time.time()
    r = run_backtest(**seed_kwargs(**overrides))
    s = summarize(r)
    s["label"] = label
    s["elapsed_s"] = round(time.time() - t0, 1)
    print(f"{label:<60s} {fmt_summary(s)}  ({s['elapsed_s']}s)")
    return s
