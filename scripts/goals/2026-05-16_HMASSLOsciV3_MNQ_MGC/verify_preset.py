"""Replay the winner preset and verify combined metrics match expectations.

The standard `_shared/preset.verify_preset` only handles single-mode presets;
this script knows how to replay the multi-asset preset shape.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from backend.api import BacktestEngineSettings, BlackoutWindowSettings  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent / "sweeps"))
from _campaign import run_multi  # noqa: E402


PRESET_PATH = Path(__file__).resolve().parent / "winner_preset.json"

EXPECTED = {
    "net_pnl": 101_921.0,
    "max_dd_$": 2_363.0,
    "trades": 2319,
    "win_rate": 51.7,
    "profit_factor": 1.615,
}
PNL_TOLERANCE = 50.0
DD_TOLERANCE = 50.0


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
    cfg_by_symbol = {c["symbol"]: c for c in preset["configs"]}
    mnq = cfg_by_symbol["MNQ"]
    mgc = cfg_by_symbol["MGC"]

    summary = run_multi(
        mnq_params={k: v for k, v in mnq["params"].items() if k != "tick_size"},
        mgc_params={k: v for k, v in mgc["params"].items() if k != "tick_size"},
        mnq_engine=engine_from_dict(mnq["engineSettings"]),
        mgc_engine=engine_from_dict(mgc["engineSettings"]),
        mnq_risk=mnq["riskPerTrade"] / 100.0,
        mgc_risk=mgc["riskPerTrade"] / 100.0,
        start=preset["startDatetime"],
        end=preset["endDatetime"],
        initial_equity=preset["initialEquity"],
        max_contracts=mnq["maxContracts"],
    )

    pnl = summary["net_pnl"]
    dd = summary["max_dd_$"]
    print(f"REPLAY: PnL=${pnl:,.2f} | DD=${dd:,.2f} | N={summary['trades']} | "
          f"WR={summary['win_rate']}% | PF={summary['profit_factor']}")
    print(f"EXPECT: PnL=${EXPECTED['net_pnl']:,.0f} | DD=${EXPECTED['max_dd_$']:,.0f} | "
          f"N={EXPECTED['trades']} | WR={EXPECTED['win_rate']}% | PF={EXPECTED['profit_factor']}")

    pnl_ok = abs(pnl - EXPECTED["net_pnl"]) < PNL_TOLERANCE
    dd_ok = abs(dd - EXPECTED["max_dd_$"]) < DD_TOLERANCE
    if pnl_ok and dd_ok:
        print("✅ MATCH")
        return 0
    print("❌ MISMATCH — investigate preset reconstruction")
    return 1


if __name__ == "__main__":
    sys.exit(main())
