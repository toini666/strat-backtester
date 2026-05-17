"""Build the multi_asset winner preset for the campaign 2026-05-17 MNQ+MGC v2.

Best valid config from step 09/10:
  - MNQ risk = 0.0048 × 0.86 = 0.4128 % (UI: 0.4128)
  - MGC risk = 0.0052       = 0.52 %   (UI: 0.52)
  - MNQ params override: mf_length = 37 (was 31)
  - MGC params override: cooldown_bars = 2 (was 1)
  - MNQ blackouts: NEW preset baseline + {5-6, 6-7}  (i.e. +BO[5, 6])
  - MGC blackouts: unchanged from NEW preset
  - Expected combined: PnL ≈ $100,076 / DD ≈ $2,009

Goal target was DD<$2,000 — we land at $2,009 (off by $9). Structural floor.
"""
from __future__ import annotations

import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

sys.path.insert(0, str(Path(__file__).resolve().parent / "sweeps"))
from _campaign import (  # noqa: E402
    INITIAL_EQUITY, MAX_CONTRACTS, MGC_BASE_PARAMS, MGC_BASE_RISK,
    MNQ_BASE_PARAMS, MNQ_BASE_RISK, START, END, STRATEGY, INTERVAL,
    run_multi, base_engine_mnq, base_engine_mgc, _bw,
)
import copy

MNQ_RISK = MNQ_BASE_RISK * 0.86          # 0.4128 %
MGC_RISK = MGC_BASE_RISK                  # 0.52 %

PRESET_NAME = (
    "[Auto] HMASSLOsciV3 — MNQ+MGC multi-asset v2 — Best valid "
    "(PnL $100.1k / DD $2.01k, DD-target $2k missed by $9)"
)

PRESETS_FILE = ROOT / "data" / "presets.json"


def mnq_blackouts() -> list[dict]:
    """MNQ blackouts: NEW preset baseline + {5-6, 6-7}."""
    return [
        # UI defaults rendered explicitly so the preset overrides them.
        {"active": False, "start_hour": 0,  "start_minute": 0,  "end_hour": 0,  "end_minute": 5},
        {"active": False, "start_hour": 9,  "start_minute": 0,  "end_hour": 9,  "end_minute": 5},
        {"active": False, "start_hour": 12, "start_minute": 0,  "end_hour": 14, "end_minute": 0},
        {"active": False, "start_hour": 15, "start_minute": 30, "end_hour": 15, "end_minute": 35},
        {"active": False, "start_hour": 16, "start_minute": 30, "end_hour": 22, "end_minute": 0},
        # Active blackouts:
        {"active": True,  "start_hour": 22, "start_minute": 0,  "end_hour": 23, "end_minute": 59},  # post-close CME
        {"active": True,  "start_hour": 11, "start_minute": 0,  "end_hour": 12, "end_minute": 0},   # NEW preset baseline
        {"active": True,  "start_hour": 14, "start_minute": 0,  "end_hour": 15, "end_minute": 0},   # NEW preset baseline
        {"active": True,  "start_hour": 8,  "start_minute": 0,  "end_hour": 9,  "end_minute": 0},   # NEW preset baseline
        {"active": True,  "start_hour": 12, "start_minute": 0,  "end_hour": 13, "end_minute": 0},   # NEW preset baseline
        # Campaign additions:
        {"active": True,  "start_hour": 5,  "start_minute": 0,  "end_hour": 6,  "end_minute": 0},   # CAMPAIGN — DD-window reducer
        {"active": True,  "start_hour": 6,  "start_minute": 0,  "end_hour": 7,  "end_minute": 0},   # CAMPAIGN — DD-window reducer
    ]


def mgc_blackouts() -> list[dict]:
    """MGC blackouts — unchanged from NEW preset."""
    return [
        {"active": False, "start_hour": 0,  "start_minute": 0,  "end_hour": 0,  "end_minute": 5},
        {"active": False, "start_hour": 9,  "start_minute": 0,  "end_hour": 9,  "end_minute": 5},
        {"active": False, "start_hour": 12, "start_minute": 0,  "end_hour": 14, "end_minute": 0},
        {"active": False, "start_hour": 15, "start_minute": 30, "end_hour": 15, "end_minute": 35},
        {"active": False, "start_hour": 16, "start_minute": 30, "end_hour": 22, "end_minute": 0},
        {"active": True,  "start_hour": 22, "start_minute": 0,  "end_hour": 23, "end_minute": 59},
        {"active": True,  "start_hour": 3,  "start_minute": 0,  "end_hour": 4,  "end_minute": 0},
        {"active": True,  "start_hour": 6,  "start_minute": 0,  "end_hour": 7,  "end_minute": 0},
        {"active": True,  "start_hour": 7,  "start_minute": 0,  "end_hour": 8,  "end_minute": 0},
        {"active": True,  "start_hour": 9,  "start_minute": 0,  "end_hour": 10, "end_minute": 0},
        {"active": True,  "start_hour": 11, "start_minute": 0,  "end_hour": 12, "end_minute": 0},
    ]


def common_engine(blackouts: list[dict]) -> dict:
    return {
        "auto_close_enabled": True,
        "auto_close_hour": 22,
        "auto_close_minute": 0,
        "blackout_windows": blackouts,
        "debug": False,
        "daily_win_limit_enabled": False,
        "daily_win_limit": 500,
        "daily_loss_limit_enabled": False,
        "daily_loss_limit": 700,
        "daily_limit_mode": "after_close",
    }


def build_mnq_params() -> dict:
    p = dict(MNQ_BASE_PARAMS)
    p["mf_length"] = 37          # campaign breakthrough
    p["tick_size"] = 0.25
    return p


def build_mgc_params() -> dict:
    p = dict(MGC_BASE_PARAMS)
    p["cooldown_bars"] = 2       # campaign breakthrough
    p["tick_size"] = 0.10        # actual MGC tick
    return p


def build_preset(metrics: dict) -> dict:
    return {
        "id": str(uuid.uuid4()),
        "name": PRESET_NAME,
        "createdAt": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "mode": "multi_asset",
        "startDatetime": START,
        "endDatetime": END,
        "initialEquity": INITIAL_EQUITY,
        "configs": [
            {
                "symbol": "MNQ",
                "interval": INTERVAL,
                "strategyName": STRATEGY,
                "params": build_mnq_params(),
                "riskPerTrade": round(MNQ_RISK * 100, 4),
                "maxContracts": MAX_CONTRACTS,
                "engineSettings": common_engine(mnq_blackouts()),
            },
            {
                "symbol": "MGC",
                "interval": INTERVAL,
                "strategyName": STRATEGY,
                "params": build_mgc_params(),
                "riskPerTrade": round(MGC_RISK * 100, 4),
                "maxContracts": MAX_CONTRACTS,
                "engineSettings": common_engine(mgc_blackouts()),
            },
        ],
        "metrics": {
            "total_return": round(metrics["net_pnl"] / INITIAL_EQUITY * 100, 4),
            "win_rate": metrics["win_rate"],
            "total_trades": metrics["trades"],
            "max_drawdown": metrics["max_dd_%"],
        },
    }


def _build_mnq_engine_obj():
    from backend.api import BlackoutWindowSettings, BacktestEngineSettings
    bws = [BlackoutWindowSettings(**w) for w in mnq_blackouts()]
    return BacktestEngineSettings(
        auto_close_enabled=True, auto_close_hour=22, auto_close_minute=0,
        blackout_windows=bws, debug=False,
        daily_win_limit_enabled=False, daily_win_limit=500.0,
        daily_loss_limit_enabled=False, daily_loss_limit=700.0,
        daily_limit_mode="after_close",
    )


def _build_mgc_engine_obj():
    from backend.api import BlackoutWindowSettings, BacktestEngineSettings
    bws = [BlackoutWindowSettings(**w) for w in mgc_blackouts()]
    return BacktestEngineSettings(
        auto_close_enabled=True, auto_close_hour=22, auto_close_minute=0,
        blackout_windows=bws, debug=False,
        daily_win_limit_enabled=False, daily_win_limit=500.0,
        daily_loss_limit_enabled=False, daily_loss_limit=700.0,
        daily_limit_mode="after_close",
    )


def main() -> None:
    print(f"Running winner config (MNQ {MNQ_RISK*100:.4f}% / MGC {MGC_RISK*100:.4f}%)...")
    summary = run_multi(
        mnq_params={"mf_length": 37},
        mgc_params={"cooldown_bars": 2},
        mnq_engine=_build_mnq_engine_obj(),
        mgc_engine=_build_mgc_engine_obj(),
        mnq_risk=MNQ_RISK, mgc_risk=MGC_RISK,
    )
    print(f"  PnL          = ${summary['net_pnl']:+,.2f}")
    print(f"  Max DD $     = ${summary['max_dd_$']:,.2f}")
    print(f"  Max DD %     = {summary['max_dd_%']:.3f}%")
    print(f"  Trades       = {summary['trades']}")
    print(f"  Win rate     = {summary['win_rate']}%")
    print(f"  Profit factor= {summary['profit_factor']}")

    preset = build_preset(summary)
    standalone = Path(__file__).resolve().parent / "winner_preset.json"
    standalone.write_text(json.dumps(preset, indent=2))
    print(f"\nWrote standalone preset: {standalone}")

    presets = json.loads(PRESETS_FILE.read_text())
    presets = [p for p in presets if p.get("name") != PRESET_NAME]
    presets.insert(0, preset)
    PRESETS_FILE.write_text(json.dumps(presets, indent=2))
    print(f"Inserted preset at head of {PRESETS_FILE}")


if __name__ == "__main__":
    main()
