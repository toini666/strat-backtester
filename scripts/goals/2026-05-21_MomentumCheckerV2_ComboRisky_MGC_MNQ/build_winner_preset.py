"""Build the WINNER multi-asset preset and insert into data/presets.json.

WINNER (Phase 08): MGC risk=0.53 %, MNQ risk=0.405 % + be_at_rr=2.4.
All other params unchanged from the COMBO RIsky preset.
Expected: PnL ≈ $106,428, DD ≈ $2,494 ($6 under $2,500 target).
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
    run_multi, fmt_multi, START, END, INITIAL_EQUITY,
    MAX_CONTRACTS, STRATEGY, INTERVAL,
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


def build_multi_preset(*, name, mgc_params, mgc_risk_pct, mgc_blackouts,
                       mnq_params, mnq_risk_pct, mnq_blackouts,
                       metrics_summary):
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


def write_preset(preset):
    WINNER_PRESET_FILE.write_text(json.dumps(preset, indent=2))
    current = json.loads(PRESETS_FILE.read_text()) if PRESETS_FILE.exists() else []
    keep = [p for p in current if p.get("name") != preset["name"]]
    keep.insert(0, preset)
    PRESETS_FILE.write_text(json.dumps(keep, indent=2))


def main():
    mgc_params = dict(MGC_PARAMS_BASE)  # identical to RIsky preset
    mgc_risk = 0.0053

    mnq_params = dict(MNQ_PARAMS_BASE)
    mnq_params["be_at_rr"] = 2.4         # +breakeven on MNQ
    mnq_risk = 0.00405                   # tightened from 0.60 %

    s = run_multi(
        mgc_params=mgc_params, mgc_risk=mgc_risk,
        mgc_blackouts=MGC_BLACKOUTS_BASE,
        mnq_params=mnq_params, mnq_risk=mnq_risk,
        mnq_blackouts=MNQ_BLACKOUTS_BASE,
    )
    print(f"WINNER replay: {fmt_multi(s)}")
    assert s["max_dd_$"] < 2500, f"DD constraint violated: ${s['max_dd_$']:.0f}"

    preset_name = (
        f"[Auto] COMBO RIsky — MGC/MNQ — "
        f"DD<$2.5k (PnL ${s['net_pnl']/1000:.1f}k / DD ${s['max_dd_$']/1000:.2f}k)"
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
