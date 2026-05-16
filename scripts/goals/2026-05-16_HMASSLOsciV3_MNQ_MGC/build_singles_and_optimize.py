"""Rewrite presets with optimized blackout windows (fewer entries, same coverage),
and create two single-mode presets — one per leg of the multi-asset winner.

Behavior preserved (every minute that was blackouted before stays blackouted):
  MNQ: 11-12 + 12-13 + 13-14 + 14-15  →  one window 11-15  (4 active → 1 active)
  MGC: 6-7 + 7-8                       →  one window 6-8   (2 active → 1 active)

Outputs:
  1. winner_preset.json (overwrite with optimized blackouts)
  2. winner_mnq_only.json (new single-mode preset)
  3. winner_mgc_only.json (new single-mode preset)
  All three inserted into data/presets.json (replacing same-named entries).
"""
from __future__ import annotations

import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from backend.api import BacktestEngineSettings, BlackoutWindowSettings  # noqa: E402
from scripts.goals._shared.harness import run_backtest, summarize  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent / "sweeps"))
from _campaign import (  # noqa: E402
    INITIAL_EQUITY, INTERVAL, MAX_CONTRACTS, MGC_BASE_PARAMS, MGC_BASE_RISK,
    MNQ_BASE_PARAMS, MNQ_BASE_RISK, START, END, STRATEGY, run_multi,
)


PRESETS_FILE = ROOT / "data" / "presets.json"

MNQ_RISK = MNQ_BASE_RISK * 1.04   # 0.003744
MGC_RISK = MGC_BASE_RISK * 1.15   # 0.005405
MNQ_RISK_PCT = round(MNQ_RISK * 100, 4)
MGC_RISK_PCT = round(MGC_RISK * 100, 4)


def mnq_blackouts() -> list[dict]:
    """Optimized MNQ blackouts: 3 active windows (08-09, 11-15, 22-23:59).
    All UI default disabled windows preserved for UI consistency.
    """
    return [
        # UI default disabled — kept for UI consistency
        {"active": False, "start_hour": 0,  "start_minute": 0,  "end_hour": 0,  "end_minute": 5},
        {"active": False, "start_hour": 9,  "start_minute": 0,  "end_hour": 9,  "end_minute": 5},
        {"active": False, "start_hour": 12, "start_minute": 0,  "end_hour": 14, "end_minute": 0},
        {"active": False, "start_hour": 15, "start_minute": 30, "end_hour": 15, "end_minute": 35},
        {"active": False, "start_hour": 16, "start_minute": 30, "end_hour": 22, "end_minute": 0},
        # Active (only 3 windows for MNQ)
        {"active": True,  "start_hour": 22, "start_minute": 0,  "end_hour": 23, "end_minute": 59},  # CME close
        {"active": True,  "start_hour": 8,  "start_minute": 0,  "end_hour": 9,  "end_minute": 0},   # new this campaign
        {"active": True,  "start_hour": 11, "start_minute": 0,  "end_hour": 15, "end_minute": 0},   # merged 11-12+12-13+13-14+14-15
    ]


def mgc_blackouts() -> list[dict]:
    """Optimized MGC blackouts: 5 active windows.
    Merge 06-07 + 07-08 → 06-08; others unchanged.
    """
    return [
        # UI default disabled
        {"active": False, "start_hour": 0,  "start_minute": 0,  "end_hour": 0,  "end_minute": 5},
        {"active": False, "start_hour": 9,  "start_minute": 0,  "end_hour": 9,  "end_minute": 5},
        {"active": False, "start_hour": 12, "start_minute": 0,  "end_hour": 14, "end_minute": 0},
        {"active": False, "start_hour": 15, "start_minute": 30, "end_hour": 15, "end_minute": 35},
        {"active": False, "start_hour": 16, "start_minute": 30, "end_hour": 22, "end_minute": 0},
        # Active (5 windows for MGC)
        {"active": True,  "start_hour": 22, "start_minute": 0,  "end_hour": 23, "end_minute": 59},  # CME close
        {"active": True,  "start_hour": 3,  "start_minute": 0,  "end_hour": 4,  "end_minute": 0},
        {"active": True,  "start_hour": 6,  "start_minute": 0,  "end_hour": 8,  "end_minute": 0},   # merged 06-07+07-08
        {"active": True,  "start_hour": 9,  "start_minute": 0,  "end_hour": 10, "end_minute": 0},
        {"active": True,  "start_hour": 11, "start_minute": 0,  "end_hour": 12, "end_minute": 0},
    ]


def make_engine(blackouts: list[dict]) -> BacktestEngineSettings:
    return BacktestEngineSettings(
        auto_close_enabled=True, auto_close_hour=22, auto_close_minute=0,
        blackout_windows=[BlackoutWindowSettings(**b) for b in blackouts],
        debug=False,
        daily_win_limit_enabled=False, daily_win_limit=500,
        daily_loss_limit_enabled=False, daily_loss_limit=700,
        daily_limit_mode="after_close",
    )


def engine_dict(blackouts: list[dict]) -> dict:
    return {
        "auto_close_enabled": True,
        "auto_close_hour": 22, "auto_close_minute": 0,
        "blackout_windows": blackouts,
        "debug": False,
        "daily_win_limit_enabled": False, "daily_win_limit": 500,
        "daily_loss_limit_enabled": False, "daily_loss_limit": 700,
        "daily_limit_mode": "after_close",
    }


def mnq_params() -> dict:
    p = dict(MNQ_BASE_PARAMS); p["tick_size"] = 0.25; return p


def mgc_params() -> dict:
    p = dict(MGC_BASE_PARAMS); p["tick_size"] = 0.10; return p


def upsert_preset(preset: dict) -> None:
    presets = json.loads(PRESETS_FILE.read_text())
    presets = [p for p in presets if p.get("name") != preset["name"]]
    presets.insert(0, preset)
    PRESETS_FILE.write_text(json.dumps(presets, indent=2))


def write_standalone(preset: dict, path: Path) -> None:
    path.write_text(json.dumps(preset, indent=2))


def main() -> None:
    print(f"{'='*100}")
    print("Verifying multi-asset replay with OPTIMIZED blackouts (should match original)...")
    print(f"{'='*100}")
    multi = run_multi(
        mnq_engine=make_engine(mnq_blackouts()),
        mgc_engine=make_engine(mgc_blackouts()),
        mnq_risk=MNQ_RISK, mgc_risk=MGC_RISK,
    )
    print(f"  multi-asset (optimized BO): PnL=${multi['net_pnl']:,.2f} | DD=${multi['max_dd_$']:,.2f} | "
          f"N={multi['trades']} | WR={multi['win_rate']}% | PF={multi['profit_factor']}")
    assert abs(multi["net_pnl"] - 101_920.86) < 1.0, "PnL drift detected!"
    assert abs(multi["max_dd_$"] - 2_362.80) < 1.0, "DD drift detected!"
    print("  ✅ optimized blackouts produce identical metrics to original\n")

    print(f"{'='*100}")
    print("Running MNQ leg standalone (single-mode)...")
    print(f"{'='*100}")
    mnq_result = run_backtest(
        strategy_name=STRATEGY, symbol="MNQ", interval=INTERVAL,
        start=START, end=END,
        strategy_params={k: v for k, v in mnq_params().items() if k != "tick_size"},
        initial_equity=INITIAL_EQUITY, risk_per_trade=MNQ_RISK,
        max_contracts=MAX_CONTRACTS, engine_settings=make_engine(mnq_blackouts()),
    )
    mnq_summary = summarize(mnq_result)
    print(f"  MNQ standalone: PnL=${mnq_summary['net_pnl']:,.2f} | DD=${mnq_summary['max_dd_$']:,.2f} | "
          f"N={mnq_summary['trades']} | WR={mnq_summary['win_rate']}% | PF={mnq_summary['profit_factor']}")

    print(f"\n{'='*100}")
    print("Running MGC leg standalone (single-mode)...")
    print(f"{'='*100}")
    mgc_result = run_backtest(
        strategy_name=STRATEGY, symbol="MGC", interval=INTERVAL,
        start=START, end=END,
        strategy_params={k: v for k, v in mgc_params().items() if k != "tick_size"},
        initial_equity=INITIAL_EQUITY, risk_per_trade=MGC_RISK,
        max_contracts=MAX_CONTRACTS, engine_settings=make_engine(mgc_blackouts()),
    )
    mgc_summary = summarize(mgc_result)
    print(f"  MGC standalone: PnL=${mgc_summary['net_pnl']:,.2f} | DD=${mgc_summary['max_dd_$']:,.2f} | "
          f"N={mgc_summary['trades']} | WR={mgc_summary['win_rate']}% | PF={mgc_summary['profit_factor']}")

    # ---- Build the three presets ----
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    # 1) Updated multi-asset winner (overwrite existing same-named preset)
    multi_name = ("[Auto] HMASSLOsciV3 — MNQ+MGC multi-asset — WINNER "
                  "(PnL $101.9k / DD $2.4k)")
    multi_preset = {
        "id": str(uuid.uuid4()),
        "name": multi_name,
        "createdAt": now,
        "mode": "multi_asset",
        "startDatetime": START,
        "endDatetime": END,
        "initialEquity": INITIAL_EQUITY,
        "configs": [
            {
                "symbol": "MNQ", "interval": INTERVAL, "strategyName": STRATEGY,
                "params": mnq_params(),
                "riskPerTrade": MNQ_RISK_PCT, "maxContracts": MAX_CONTRACTS,
                "engineSettings": engine_dict(mnq_blackouts()),
            },
            {
                "symbol": "MGC", "interval": INTERVAL, "strategyName": STRATEGY,
                "params": mgc_params(),
                "riskPerTrade": MGC_RISK_PCT, "maxContracts": MAX_CONTRACTS,
                "engineSettings": engine_dict(mgc_blackouts()),
            },
        ],
        "metrics": {
            "total_return": round(multi["net_pnl"] / INITIAL_EQUITY * 100, 4),
            "win_rate": multi["win_rate"],
            "total_trades": multi["trades"],
            "max_drawdown": multi["max_dd_%"],
        },
    }
    write_standalone(multi_preset, Path(__file__).resolve().parent / "winner_preset.json")
    upsert_preset(multi_preset)
    print(f"\n→ Updated multi-asset preset: '{multi_name}'")

    # 2) MNQ-only single-mode preset
    mnq_name = (f"[Auto] HMASSLOsciV3 — MNQ 7m — multi-leg config "
                f"(PnL ${mnq_summary['net_pnl']/1000:.1f}k / DD ${mnq_summary['max_dd_$']/1000:.2f}k)")
    mnq_preset = {
        "id": str(uuid.uuid4()),
        "name": mnq_name,
        "createdAt": now,
        "mode": "single",
        "symbol": "MNQ",
        "interval": INTERVAL,
        "startDatetime": START,
        "endDatetime": END,
        "initialEquity": INITIAL_EQUITY,
        "riskPerTrade": MNQ_RISK_PCT,
        "maxContracts": MAX_CONTRACTS,
        "strategyName": STRATEGY,
        "params": mnq_params(),
        "engineSettings": engine_dict(mnq_blackouts()),
        "metrics": {
            "total_return": round(mnq_summary["net_pnl"] / INITIAL_EQUITY * 100, 4),
            "win_rate": mnq_summary["win_rate"],
            "total_trades": mnq_summary["trades"],
            "max_drawdown": mnq_summary["max_dd_%"],
        },
    }
    write_standalone(mnq_preset, Path(__file__).resolve().parent / "winner_mnq_only.json")
    upsert_preset(mnq_preset)
    print(f"→ MNQ single preset: '{mnq_name}'")

    # 3) MGC-only single-mode preset
    mgc_name = (f"[Auto] HMASSLOsciV3 — MGC 7m — multi-leg config "
                f"(PnL ${mgc_summary['net_pnl']/1000:.1f}k / DD ${mgc_summary['max_dd_$']/1000:.2f}k)")
    mgc_preset = {
        "id": str(uuid.uuid4()),
        "name": mgc_name,
        "createdAt": now,
        "mode": "single",
        "symbol": "MGC",
        "interval": INTERVAL,
        "startDatetime": START,
        "endDatetime": END,
        "initialEquity": INITIAL_EQUITY,
        "riskPerTrade": MGC_RISK_PCT,
        "maxContracts": MAX_CONTRACTS,
        "strategyName": STRATEGY,
        "params": mgc_params(),
        "engineSettings": engine_dict(mgc_blackouts()),
        "metrics": {
            "total_return": round(mgc_summary["net_pnl"] / INITIAL_EQUITY * 100, 4),
            "win_rate": mgc_summary["win_rate"],
            "total_trades": mgc_summary["trades"],
            "max_drawdown": mgc_summary["max_dd_%"],
        },
    }
    write_standalone(mgc_preset, Path(__file__).resolve().parent / "winner_mgc_only.json")
    upsert_preset(mgc_preset)
    print(f"→ MGC single preset: '{mgc_name}'")

    print("\nAll three presets written to data/presets.json (top of list).")


if __name__ == "__main__":
    main()
