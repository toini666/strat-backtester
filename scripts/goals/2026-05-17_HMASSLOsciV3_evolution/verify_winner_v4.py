"""Verify chaque winner V4 reproduit ses métriques.

Run :  python scripts/goals/2026-05-17_HMASSLOsciV3_evolution/verify_winner_v4.py

Doit afficher ✅ MATCH pour chaque asset.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from scripts.goals._shared.preset import verify_preset  # noqa: E402

HERE = Path(__file__).resolve().parent

# === MAJ après Phase 3 ====================================================
# MGC only — MNQ had no improving combo.
EXPECTED: dict[str, dict] = {
    "winner_v4_MGC.json": {
        "net_pnl": 47_164,
        "max_dd_$": 1_971,
        "trades": 824,
        "win_rate": 55.3,
        "profit_factor": 1.71,
    },
}
# ==========================================================================


def main():
    if not EXPECTED:
        print("⚠️  EXPECTED is empty — fill in after Phase 3 winner combos.")
        sys.exit(0)
    all_ok = True
    for fname, exp in EXPECTED.items():
        p = HERE / fname
        if not p.exists():
            print(f"❌ Missing preset {p}")
            all_ok = False
            continue
        print(f"\n--- {fname} ---")
        ok = verify_preset(p, exp, pnl_tolerance=50.0, dd_tolerance=50.0)
        if not ok:
            all_ok = False
    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
