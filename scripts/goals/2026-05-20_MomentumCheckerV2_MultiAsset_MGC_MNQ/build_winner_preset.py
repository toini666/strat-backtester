"""Build the winning multi-asset preset and write it into data/presets.json.

The shared `build_preset` helper is single-asset only — multi-asset presets
have a different shape (`mode: "multi_asset"`, `configs: [...]`). This script
constructs the multi-asset preset and writes both standalone JSON and
inserts/replaces in data/presets.json.

IMPORTANT: stores `max_drawdown_dollars` in the metrics so the UI
FavoritesPage reads the true peak-to-trough $DD (not the %×initial_equity
fallback that mis-states multi-asset DD$).
"""
from __future__ import annotations

import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

sys.path.insert(0, str(Path(__file__).resolve().parent / "sweeps"))
from _campaign import (  # noqa: E402
    MGC_PARAMS_BASE, MNQ_PARAMS_BASE,
    MGC_BLACKOUTS_BASE, MNQ_BLACKOUTS_BASE,
    run_multi, fmt_multi, START, END, INITIAL_EQUITY, MAX_CONTRACTS, STRATEGY, INTERVAL,
)


PRESETS_FILE = ROOT / "data" / "presets.json"
WINNER_PRESET_FILE = Path(__file__).resolve().parent / "winner_preset.json"


def _engine_dict(blackouts):
    return {
        "auto_close_enabled": True,
        "auto_close_hour": 22,
        "auto_close_minute": 0,
        "blackout_windows": [
            {
                "active": True,
                "start_hour": h1, "start_minute": m1,
                "end_hour": h2, "end_minute": m2,
            }
            for (h1, m1, h2, m2) in blackouts
        ],
        "debug": False,
        "daily_win_limit_enabled": False,
        "daily_win_limit": 500,
        "daily_loss_limit_enabled": False,
        "daily_loss_limit": 700,
        "daily_limit_mode": "after_close",
    }


def build_multi_preset(
    *,
    name: str,
    mgc_params: dict,
    mgc_risk_pct: float,
    mgc_blackouts: list,
    mnq_params: dict,
    mnq_risk_pct: float,
    mnq_blackouts: list,
    metrics_summary: dict,
) -> dict:
    """Construct a multi-asset preset matching the UI shape."""
    return {
        "id": str(uuid.uuid4()),
        "name": name,
        "createdAt": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "mode": "multi_asset",
        "startDatetime": START,
        "endDatetime": END,
        "initialEquity": INITIAL_EQUITY,
        "configs": [
            {
                "symbol": "MGC",
                "interval": INTERVAL,
                "strategyName": STRATEGY,
                "params": mgc_params,
                "riskPerTrade": mgc_risk_pct,
                "maxContracts": MAX_CONTRACTS,
                "engineSettings": _engine_dict(mgc_blackouts),
            },
            {
                "symbol": "MNQ",
                "interval": INTERVAL,
                "strategyName": STRATEGY,
                "params": mnq_params,
                "riskPerTrade": mnq_risk_pct,
                "maxContracts": MAX_CONTRACTS,
                "engineSettings": _engine_dict(mnq_blackouts),
            },
        ],
        "metrics": {
            "total_return": metrics_summary["net_pnl"] / INITIAL_EQUITY * 100,
            "win_rate": metrics_summary["win_rate"],
            "total_trades": metrics_summary["trades"],
            "max_drawdown": metrics_summary["max_dd_%"],
            "max_drawdown_dollars": metrics_summary["max_dd_$"],
        },
    }


def write_preset(preset: dict):
    WINNER_PRESET_FILE.write_text(json.dumps(preset, indent=2))
    if PRESETS_FILE.exists():
        current = json.loads(PRESETS_FILE.read_text())
    else:
        current = []
    keep = [p for p in current if p.get("name") != preset["name"]]
    keep.insert(0, preset)
    PRESETS_FILE.write_text(json.dumps(keep, indent=2))


def main():
    """Build the final winner preset from Phase 16 lock."""
    # LOCKED WINNER (Phase 16): MGC=0.53% MNQ=0.345% mcp=0.26 MNQ_be=2.4
    # mgc params: sl_max_points=80, max_candle_pct=0.26, be_at_rr=2.0
    # mnq params: be_at_rr=2.4
    # Expected: PnL=$96,428 / DD=$2,254 (margin $46 under $2,300 ceiling)
    mgc_params = dict(MGC_PARAMS_BASE)
    mgc_params["sl_max_points"] = 80
    mgc_params["max_candle_pct"] = 0.26
    mgc_params["be_at_rr"] = 2.0
    mgc_risk = 0.0053

    mnq_params = dict(MNQ_PARAMS_BASE)
    mnq_params["be_at_rr"] = 2.4
    mnq_risk = 0.00345

    s = run_multi(
        mgc_params=mgc_params, mgc_risk=mgc_risk,
        mgc_blackouts=MGC_BLACKOUTS_BASE,
        mnq_params=mnq_params, mnq_risk=mnq_risk,
        mnq_blackouts=MNQ_BLACKOUTS_BASE,
    )
    print(f"WINNER replay: {fmt_multi(s)}")

    preset_name = (
        f"[Auto] MomentumCheckerV2 — MGC+MNQ multi-asset — "
        f"DD<$2.3k (PnL ${s['net_pnl']/1000:.1f}k / DD ${s['max_dd_$']/1000:.2f}k)"
    )
    preset = build_multi_preset(
        name=preset_name,
        mgc_params=mgc_params, mgc_risk_pct=mgc_risk * 100,
        mgc_blackouts=MGC_BLACKOUTS_BASE,
        mnq_params=mnq_params, mnq_risk_pct=mnq_risk * 100,
        mnq_blackouts=MNQ_BLACKOUTS_BASE,
        metrics_summary=s,
    )
    write_preset(preset)
    print(f"Wrote preset → {WINNER_PRESET_FILE}")
    print(f"Inserted into → {PRESETS_FILE}")
    print(f"  Name: {preset['name']}")


if __name__ == "__main__":
    main()
