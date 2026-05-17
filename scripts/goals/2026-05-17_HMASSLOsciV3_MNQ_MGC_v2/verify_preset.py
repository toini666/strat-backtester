"""Verify the multi_asset winner preset replays to the expected metrics.

The shared `_shared/preset.py::verify_preset` only handles single-mode presets;
multi_asset presets are verified here by replaying both legs and recombining
through `_apply_combined_daily_limits`.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

sys.path.insert(0, str(Path(__file__).resolve().parent / "sweeps"))
from _campaign import (  # noqa: E402
    INITIAL_EQUITY, INTERVAL, MAX_CONTRACTS, STRATEGY,
    _apply_combined_daily_limits, _combined_dd_dollars, _trades_with_source,
    run_multi,
)
from backend.api import BacktestEngineSettings, BlackoutWindowSettings  # noqa: E402


PRESET_PATH = Path(__file__).resolve().parent / "winner_preset.json"

EXPECTED = {
    "net_pnl": 100_076,
    "max_dd_$": 2_009,
    "trades": 1970,
    "win_rate": 51.22,
    "profit_factor": 1.698,
}

PNL_TOL = 100.0
DD_TOL  = 50.0


def engine_from_dict(d):
    return BacktestEngineSettings(
        auto_close_enabled=d["auto_close_enabled"],
        auto_close_hour=d["auto_close_hour"],
        auto_close_minute=d["auto_close_minute"],
        blackout_windows=[BlackoutWindowSettings(**w) for w in d["blackout_windows"]],
        debug=d.get("debug", False),
        daily_win_limit_enabled=d["daily_win_limit_enabled"],
        daily_win_limit=d["daily_win_limit"],
        daily_loss_limit_enabled=d["daily_loss_limit_enabled"],
        daily_loss_limit=d["daily_loss_limit"],
        daily_limit_mode=d["daily_limit_mode"],
    )


def main() -> int:
    preset = json.loads(PRESET_PATH.read_text())
    assert preset["mode"] == "multi_asset", "expected multi_asset preset"
    mnq_cfg, mgc_cfg = preset["configs"][0], preset["configs"][1]
    assert mnq_cfg["symbol"] == "MNQ" and mgc_cfg["symbol"] == "MGC"

    mnq_overrides = {k: v for k, v in mnq_cfg["params"].items() if k != "tick_size"}
    mgc_overrides = {k: v for k, v in mgc_cfg["params"].items() if k != "tick_size"}

    summary = run_multi(
        mnq_params=mnq_overrides,
        mgc_params=mgc_overrides,
        mnq_engine=engine_from_dict(mnq_cfg["engineSettings"]),
        mgc_engine=engine_from_dict(mgc_cfg["engineSettings"]),
        mnq_risk=mnq_cfg["riskPerTrade"] / 100.0,
        mgc_risk=mgc_cfg["riskPerTrade"] / 100.0,
        start=preset["startDatetime"],
        end=preset["endDatetime"],
        initial_equity=preset["initialEquity"],
        max_contracts=mnq_cfg["maxContracts"],
    )

    print(f"PRESET REPLAY:  PnL=${summary['net_pnl']:,.0f}  DD=${summary['max_dd_$']:,.0f}  "
          f"N={summary['trades']}  WR={summary['win_rate']:.2f}%  PF={summary['profit_factor']}")
    print(f"Expected:       PnL=${EXPECTED['net_pnl']:,}  DD=${EXPECTED['max_dd_$']:,}  "
          f"N={EXPECTED['trades']}  WR={EXPECTED['win_rate']}%  PF={EXPECTED['profit_factor']}")
    pnl_ok = abs(summary["net_pnl"] - EXPECTED["net_pnl"]) < PNL_TOL
    dd_ok  = abs(summary["max_dd_$"] - EXPECTED["max_dd_$"]) < DD_TOL
    if pnl_ok and dd_ok:
        print("✅ MATCH")
        return 0
    print("❌ MISMATCH — investigate preset reconstruction")
    return 1


if __name__ == "__main__":
    sys.exit(main())
