"""Build, write, and verify backtest presets — the bridge between a goal
campaign's winning config and the UI's favorites list.

The preset format matches what the UI expects (frontend/src/api.ts:
SingleBacktestPreset). Risk is stored as a PERCENT (0.6 = 0.6%).
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from backend.api import BacktestEngineSettings, BlackoutWindowSettings, STRATEGIES, load_strategies

from .harness import run_backtest, summarize, fmt_summary


ROOT = Path(__file__).resolve().parents[3]
PRESETS_FILE = ROOT / "data" / "presets.json"


def engine_to_dict(es: BacktestEngineSettings) -> Dict[str, Any]:
    return {
        "auto_close_enabled": es.auto_close_enabled,
        "auto_close_hour": es.auto_close_hour,
        "auto_close_minute": es.auto_close_minute,
        "blackout_windows": [
            {
                "active": w.active,
                "start_hour": w.start_hour,
                "start_minute": w.start_minute,
                "end_hour": w.end_hour,
                "end_minute": w.end_minute,
            }
            for w in es.blackout_windows
        ],
        "debug": es.debug,
        "daily_win_limit_enabled": es.daily_win_limit_enabled,
        "daily_win_limit": es.daily_win_limit,
        "daily_loss_limit_enabled": es.daily_loss_limit_enabled,
        "daily_loss_limit": es.daily_loss_limit,
        "daily_limit_mode": es.daily_limit_mode,
    }


def engine_from_dict(d: Dict[str, Any]) -> BacktestEngineSettings:
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


def build_preset(
    *,
    strategy_name: str,
    symbol: str,
    interval: str,
    start: str,
    end: str,
    initial_equity: float,
    risk_per_trade_decimal: float,  # 0.006 → stored as 0.6 (%)
    max_contracts: int,
    strategy_param_overrides: Dict[str, Any],
    engine_settings: BacktestEngineSettings,
    metrics_summary: Dict[str, Any],
    name: Optional[str] = None,
) -> Dict[str, Any]:
    """Build a complete preset dict ready to be written to `data/presets.json`.

    `strategy_param_overrides` is merged on top of `default_params` so the
    preset is self-contained (UI reads every key).
    """
    load_strategies()
    strat_cls = STRATEGIES[strategy_name]
    full_params = dict(strat_cls.default_params)
    full_params.update(strategy_param_overrides or {})

    if name is None:
        net = metrics_summary.get("net_pnl", 0)
        dd = metrics_summary.get("max_dd_$", 0)
        name = (
            f"[Auto] {strategy_name} — {symbol} {interval} — WINNER "
            f"(PnL ${net/1000:.1f}k / DD ${dd/1000:.1f}k)"
        )

    return {
        "id": str(uuid.uuid4()),
        "name": name,
        "createdAt": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "mode": "single",
        "symbol": symbol,
        "interval": interval,
        "startDatetime": start,
        "endDatetime": end,
        "initialEquity": initial_equity,
        # UI stores risk as percent; backend uses decimal. Convert.
        "riskPerTrade": round(risk_per_trade_decimal * 100, 4),
        "maxContracts": max_contracts,
        "strategyName": strategy_name,
        "params": full_params,
        "engineSettings": engine_to_dict(engine_settings),
        "metrics": {
            "total_return": metrics_summary.get("net_pnl", 0) / max(initial_equity, 1) * 100,
            "win_rate": metrics_summary.get("win_rate", 0),
            "total_trades": metrics_summary.get("trades", 0),
            "max_drawdown": metrics_summary.get("max_dd_%", 0),
            "max_drawdown_dollars": metrics_summary.get("max_dd_$", 0),
        },
    }


def write_preset(preset: Dict[str, Any], standalone_path: Path,
                 insert_into_presets_json: bool = True) -> None:
    """Write preset to `standalone_path` and (by default) insert into data/presets.json."""
    standalone_path.parent.mkdir(parents=True, exist_ok=True)
    standalone_path.write_text(json.dumps(preset, indent=2))

    if insert_into_presets_json:
        if PRESETS_FILE.exists():
            current = json.loads(PRESETS_FILE.read_text())
        else:
            current = []
        # Replace existing preset with same name, else prepend
        keep = [p for p in current if p.get("name") != preset["name"]]
        keep.insert(0, preset)
        PRESETS_FILE.write_text(json.dumps(keep, indent=2))


def replay_preset(preset_path: Path) -> Dict[str, Any]:
    """Load a preset JSON, run the backtest, return summary."""
    preset = json.loads(Path(preset_path).read_text())
    engine = engine_from_dict(preset["engineSettings"])
    strategy_overrides = {k: v for k, v in preset["params"].items() if k != "tick_size"}
    r = run_backtest(
        strategy_name=preset["strategyName"],
        symbol=preset["symbol"],
        interval=preset["interval"],
        start=preset["startDatetime"],
        end=preset["endDatetime"],
        strategy_params=strategy_overrides,
        initial_equity=preset["initialEquity"],
        risk_per_trade=preset["riskPerTrade"] / 100.0,
        max_contracts=preset["maxContracts"],
        engine_settings=engine,
    )
    return summarize(r)


def verify_preset(preset_path: Path, expected: Dict[str, Any],
                  pnl_tolerance: float = 50.0, dd_tolerance: float = 50.0) -> bool:
    """Replay a preset and verify metrics match `expected` within tolerance.

    `expected` keys: net_pnl, max_dd_$, trades, win_rate, profit_factor.
    Returns True if match, prints ✅ / ❌.
    """
    s = replay_preset(preset_path)
    print(f"PRESET REPLAY: {fmt_summary(s)}")
    print(f"Expected:      PnL=${expected['net_pnl']:,.0f} DD=${expected['max_dd_$']:,.0f} "
          f"N={expected['trades']} WR={expected['win_rate']}% PF={expected['profit_factor']}")
    pnl_ok = abs(s["net_pnl"] - expected["net_pnl"]) < pnl_tolerance
    dd_ok = abs(s["max_dd_$"] - expected["max_dd_$"]) < dd_tolerance
    if pnl_ok and dd_ok:
        print("✅ MATCH")
        return True
    print("❌ MISMATCH — investigate preset reconstruction")
    return False
