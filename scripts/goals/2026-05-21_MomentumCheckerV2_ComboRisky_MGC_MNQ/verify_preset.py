"""Replay winner_preset.json through both harness and backend `run_multi_backtest`."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

sys.path.insert(0, str(Path(__file__).resolve().parent / "sweeps"))
from _campaign import run_multi, fmt_multi, _combined_metrics, INITIAL_EQUITY  # noqa: E402

WINNER_PRESET_FILE = Path(__file__).resolve().parent / "winner_preset.json"


def main():
    preset = json.loads(WINNER_PRESET_FILE.read_text())
    print(f"Replaying preset: {preset['name']}\n")

    mgc_cfg = next(c for c in preset["configs"] if c["symbol"] == "MGC")
    mnq_cfg = next(c for c in preset["configs"] if c["symbol"] == "MNQ")

    def cfg_to_blackouts(cfg):
        return [
            (w["start_hour"], w["start_minute"], w["end_hour"], w["end_minute"])
            for w in cfg["engineSettings"]["blackout_windows"]
            if w.get("active", True)
        ]

    s = run_multi(
        mgc_params={k: v for k, v in mgc_cfg["params"].items() if k != "tick_size"},
        mgc_risk=mgc_cfg["riskPerTrade"] / 100.0,
        mgc_blackouts=cfg_to_blackouts(mgc_cfg),
        mnq_params={k: v for k, v in mnq_cfg["params"].items() if k != "tick_size"},
        mnq_risk=mnq_cfg["riskPerTrade"] / 100.0,
        mnq_blackouts=cfg_to_blackouts(mnq_cfg),
    )
    print(f"REPLAY (harness): {fmt_multi(s)}")

    expected_pnl = preset["metrics"]["total_return"] / 100.0 * INITIAL_EQUITY
    expected_dd = preset["metrics"].get("max_drawdown_dollars", 0.0)
    print(f"Expected:         PnL=${expected_pnl:,.0f} DD=${expected_dd:,.0f}")

    pnl_ok = abs(s["net_pnl"] - expected_pnl) < 50
    dd_ok = abs(s["max_dd_$"] - expected_dd) < 50

    print()
    print("Cross-check: backend run_multi_backtest")
    from backend.api import (
        MultiBacktestRequest, MultiBacktestConfig, BacktestEngineSettings,
        BlackoutWindowSettings, run_multi_backtest, load_strategies,
    )

    def _cfg_to_engine(cfg):
        es = cfg["engineSettings"]
        return BacktestEngineSettings(
            auto_close_enabled=es["auto_close_enabled"],
            auto_close_hour=es["auto_close_hour"],
            auto_close_minute=es["auto_close_minute"],
            blackout_windows=[BlackoutWindowSettings(**w) for w in es["blackout_windows"]],
            debug=es.get("debug", False),
            daily_win_limit_enabled=es["daily_win_limit_enabled"],
            daily_win_limit=es["daily_win_limit"],
            daily_loss_limit_enabled=es["daily_loss_limit_enabled"],
            daily_loss_limit=es["daily_loss_limit"],
            daily_limit_mode=es["daily_limit_mode"],
        )

    load_strategies()
    req = MultiBacktestRequest(
        mode="multi_asset",
        start_datetime=preset["startDatetime"],
        end_datetime=preset["endDatetime"],
        initial_equity=preset["initialEquity"],
        configs=[
            MultiBacktestConfig(
                strategy_name=mgc_cfg["strategyName"],
                symbol=mgc_cfg["symbol"],
                interval=mgc_cfg["interval"],
                params={k: v for k, v in mgc_cfg["params"].items() if k != "tick_size"},
                risk_per_trade=mgc_cfg["riskPerTrade"] / 100.0,
                max_contracts=mgc_cfg["maxContracts"],
                engine_settings=_cfg_to_engine(mgc_cfg),
            ),
            MultiBacktestConfig(
                strategy_name=mnq_cfg["strategyName"],
                symbol=mnq_cfg["symbol"],
                interval=mnq_cfg["interval"],
                params={k: v for k, v in mnq_cfg["params"].items() if k != "tick_size"},
                risk_per_trade=mnq_cfg["riskPerTrade"] / 100.0,
                max_contracts=mnq_cfg["maxContracts"],
                engine_settings=_cfg_to_engine(mnq_cfg),
            ),
        ],
    )
    res = run_multi_backtest(req)
    trades_dicts = [t.model_dump() for t in res.trades]
    backend_summary = _combined_metrics(preset["initialEquity"], trades_dicts)
    print(f"BACKEND replay:  PnL=${backend_summary['net_pnl']:>9,.0f} | "
          f"DD=${backend_summary['max_dd_$']:>6,.0f} | N={backend_summary['trades']}")
    print(f"  Backend metrics.max_drawdown (%): {res.metrics.get('max_drawdown', 0):.4f}")

    harness_vs_backend_pnl = abs(s["net_pnl"] - backend_summary["net_pnl"])
    harness_vs_backend_dd = abs(s["max_dd_$"] - backend_summary["max_dd_$"])
    print(f"  harness vs backend: PnL Δ=${harness_vs_backend_pnl:.0f}, DD Δ=${harness_vs_backend_dd:.0f}")
    cross_ok = harness_vs_backend_pnl < 5 and harness_vs_backend_dd < 5

    print()
    if pnl_ok and dd_ok and cross_ok:
        print("✅ MATCH (harness reproduces preset, backend agrees)")
        return 0
    else:
        print("❌ MISMATCH")
        if not pnl_ok:
            print(f"  PnL mismatch: ${s['net_pnl']} vs ${expected_pnl}")
        if not dd_ok:
            print(f"  DD mismatch:  ${s['max_dd_$']} vs ${expected_dd}")
        if not cross_ok:
            print(f"  Backend cross-check failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
