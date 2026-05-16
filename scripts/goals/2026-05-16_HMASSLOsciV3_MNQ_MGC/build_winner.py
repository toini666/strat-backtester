"""Build the multi_asset winner preset and insert it into data/presets.json.

The preset is multi_asset (mode = "multi_asset"); the shared _shared/preset.py
only knows the "single" mode, so this helper produces the multi-asset structure
by hand (mirroring the existing `HMA-SSL-V3 - MNQ/MGC - Best` baseline shape).

Winner:
  MNQ blackouts: 22-23:59, 11-12, 14-15 (baseline) + 8-9, 12-13, 13-14 (NEW)
  MGC blackouts: 22-23:59, 11-12, 6-7, 7-8, 3-4, 9-10 (unchanged from baseline)
  MNQ risk_per_trade: 0.36% × 1.04 = 0.3744%
  MGC risk_per_trade: 0.47% × 1.15 = 0.5405%
  Expected combined: PnL ≈ $101,921 / DD ≈ $2,363 / P/DD ≈ 43.1
"""
from __future__ import annotations

import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from scripts.goals._shared.harness import run_backtest  # noqa: E402
from scripts.goals._shared.engine_settings import ui_default_engine_settings  # noqa: E402

# Reuse local helpers
sys.path.insert(0, str(Path(__file__).resolve().parent / "sweeps"))
from _campaign import (  # noqa: E402
    INITIAL_EQUITY, MAX_CONTRACTS, MGC_BASE_PARAMS, MGC_BASE_RISK,
    MNQ_BASE_PARAMS, MNQ_BASE_RISK, START, END, STRATEGY, INTERVAL,
    run_multi,
)


# Risk multipliers for the winner.
MNQ_RISK_PCT = round(MNQ_BASE_RISK * 1.04 * 100, 4)  # 0.3744
MGC_RISK_PCT = round(MGC_BASE_RISK * 1.15 * 100, 4)  # 0.5405

PRESET_NAME = (
    "[Auto] HMASSLOsciV3 — MNQ+MGC multi-asset — WINNER "
    "(PnL $101.9k / DD $2.4k)"
)

PRESETS_FILE = ROOT / "data" / "presets.json"


def mnq_blackouts() -> list[dict]:
    """Full MNQ blackout list (active + inactive) — UI defaults overridden."""
    return [
        # UI defaults rendered explicitly so the preset is self-contained.
        {"active": False, "start_hour": 0,  "start_minute": 0,  "end_hour": 0,  "end_minute": 5},
        {"active": False, "start_hour": 9,  "start_minute": 0,  "end_hour": 9,  "end_minute": 5},
        {"active": False, "start_hour": 12, "start_minute": 0,  "end_hour": 14, "end_minute": 0},
        {"active": False, "start_hour": 15, "start_minute": 30, "end_hour": 15, "end_minute": 35},
        {"active": False, "start_hour": 16, "start_minute": 30, "end_hour": 22, "end_minute": 0},
        # Active blackouts:
        {"active": True,  "start_hour": 22, "start_minute": 0,  "end_hour": 23, "end_minute": 59},  # post-close CME
        {"active": True,  "start_hour": 11, "start_minute": 0,  "end_hour": 12, "end_minute": 0},   # baseline
        {"active": True,  "start_hour": 14, "start_minute": 0,  "end_hour": 15, "end_minute": 0},   # baseline
        {"active": True,  "start_hour": 8,  "start_minute": 0,  "end_hour": 9,  "end_minute": 0},   # NEW v1
        {"active": True,  "start_hour": 12, "start_minute": 0,  "end_hour": 13, "end_minute": 0},   # NEW v1
        {"active": True,  "start_hour": 13, "start_minute": 0,  "end_hour": 14, "end_minute": 0},   # NEW v1
    ]


def mgc_blackouts() -> list[dict]:
    """Full MGC blackout list — copied from baseline preset (unchanged)."""
    return [
        {"active": False, "start_hour": 0,  "start_minute": 0,  "end_hour": 0,  "end_minute": 5},
        {"active": False, "start_hour": 9,  "start_minute": 0,  "end_hour": 9,  "end_minute": 5},
        {"active": False, "start_hour": 12, "start_minute": 0,  "end_hour": 14, "end_minute": 0},
        {"active": False, "start_hour": 15, "start_minute": 30, "end_hour": 15, "end_minute": 35},
        {"active": False, "start_hour": 16, "start_minute": 30, "end_hour": 22, "end_minute": 0},
        {"active": True,  "start_hour": 22, "start_minute": 0,  "end_hour": 23, "end_minute": 59},
        {"active": True,  "start_hour": 11, "start_minute": 0,  "end_hour": 12, "end_minute": 0},
        {"active": True,  "start_hour": 6,  "start_minute": 0,  "end_hour": 7,  "end_minute": 0},
        {"active": True,  "start_hour": 7,  "start_minute": 0,  "end_hour": 8,  "end_minute": 0},
        {"active": True,  "start_hour": 3,  "start_minute": 0,  "end_hour": 4,  "end_minute": 0},
        {"active": True,  "start_hour": 9,  "start_minute": 0,  "end_hour": 10, "end_minute": 0},
    ]


def common_engine_settings(blackouts: list[dict]) -> dict:
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
    params = dict(MNQ_BASE_PARAMS)
    params["tick_size"] = 0.25
    return params


def build_mgc_params() -> dict:
    params = dict(MGC_BASE_PARAMS)
    params["tick_size"] = 0.10  # MGC actual tick (UI value matches simulator override).
    return params


def build_preset(combined_metrics: dict) -> dict:
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
                "riskPerTrade": MNQ_RISK_PCT,
                "maxContracts": MAX_CONTRACTS,
                "engineSettings": common_engine_settings(mnq_blackouts()),
            },
            {
                "symbol": "MGC",
                "interval": INTERVAL,
                "strategyName": STRATEGY,
                "params": build_mgc_params(),
                "riskPerTrade": MGC_RISK_PCT,
                "maxContracts": MAX_CONTRACTS,
                "engineSettings": common_engine_settings(mgc_blackouts()),
            },
        ],
        "metrics": {
            "total_return": round(combined_metrics["net_pnl"] / INITIAL_EQUITY * 100, 4),
            "win_rate": combined_metrics["win_rate"],
            "total_trades": combined_metrics["trades"],
            "max_drawdown": combined_metrics["max_dd_%"],
        },
    }


def main() -> None:
    print("Running winner config to capture metrics...")
    summary = run_multi(
        mnq_risk=MNQ_BASE_RISK * 1.04,
        mgc_risk=MGC_BASE_RISK * 1.15,
        mnq_engine=__import__("backend.api", fromlist=["BacktestEngineSettings"]).BacktestEngineSettings(
            **{
                "auto_close_enabled": True, "auto_close_hour": 22, "auto_close_minute": 0,
                "blackout_windows": [
                    __import__("backend.api", fromlist=["BlackoutWindowSettings"]).BlackoutWindowSettings(**b)
                    for b in mnq_blackouts()
                ],
                "debug": False,
                "daily_win_limit_enabled": False, "daily_win_limit": 500,
                "daily_loss_limit_enabled": False, "daily_loss_limit": 700,
                "daily_limit_mode": "after_close",
            }
        ),
        mgc_engine=__import__("backend.api", fromlist=["BacktestEngineSettings"]).BacktestEngineSettings(
            **{
                "auto_close_enabled": True, "auto_close_hour": 22, "auto_close_minute": 0,
                "blackout_windows": [
                    __import__("backend.api", fromlist=["BlackoutWindowSettings"]).BlackoutWindowSettings(**b)
                    for b in mgc_blackouts()
                ],
                "debug": False,
                "daily_win_limit_enabled": False, "daily_win_limit": 500,
                "daily_loss_limit_enabled": False, "daily_loss_limit": 700,
                "daily_limit_mode": "after_close",
            }
        ),
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
