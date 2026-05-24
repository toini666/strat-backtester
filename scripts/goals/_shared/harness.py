"""Strategy-agnostic backtest harness for goal campaigns.

Calls the engine directly (no HTTP) and caches bars between runs.
"""

from __future__ import annotations

import sys
import time
from datetime import timedelta
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.api import (  # noqa: E402
    BACKTEST_TZ,
    BacktestEngineSettings,
    DEFAULT_WARMUP_BARS,
    STRATEGIES,
    STRATEGY_WARMUP_BARS,
    _annotate_blackout_flags,
    _build_blackout_windows,
    _contract_backtest_specs,
    _normalize_backtest_datetime,
    _slice_from_start,
    load_strategies,
)
from src.data import market_store as ms_module  # noqa: E402
from src.data.market_store import SYMBOL_CONTRACTS  # noqa: E402
from src.engine.simulator import SimulatorConfig, simulate as simulate_strategy  # noqa: E402

from .engine_settings import ui_default_engine_settings


_DATA_CACHE: Dict[Tuple, pd.DataFrame] = {}
_DATA_1M_CACHE: Dict[Tuple, pd.DataFrame] = {}


def _load_data(symbol: str, contract_id: str, interval: str,
               original_start: pd.Timestamp, end: pd.Timestamp,
               warmup_bars: int) -> Tuple[pd.DataFrame, pd.DataFrame, pd.Timestamp]:
    map_min = {"1m": 1, "2m": 2, "3m": 3, "5m": 5, "7m": 7, "10m": 10, "15m": 15}
    minutes_per_bar = map_min.get(interval, 15)
    trading_minutes_needed = warmup_bars * minutes_per_bar
    trading_days = trading_minutes_needed / (23 * 60)
    calendar_days = max(2, int(trading_days * 7 / 5) + 3)
    start_date = original_start - timedelta(days=calendar_days)

    ds_meta = ms_module.MarketDataStore().get_dataset_by_symbol(symbol)
    if ds_meta:
        ds_start = pd.Timestamp(ds_meta["start_date"])
        if ds_start.tzinfo is None:
            ds_start = ds_start.tz_localize(BACKTEST_TZ)
        if start_date < ds_start:
            start_date = ds_start

    key = (symbol, interval, str(start_date), str(end))
    if key not in _DATA_CACHE:
        store = ms_module.MarketDataStore()
        _DATA_CACHE[key] = store.load_bars(contract_id, start_date, end, interval)
    key_1m = (symbol, "1m", str(start_date), str(end))
    if key_1m not in _DATA_1M_CACHE:
        store = ms_module.MarketDataStore()
        _DATA_1M_CACHE[key_1m] = store.load_bars(contract_id, start_date, end, "1m")

    return _DATA_CACHE[key], _DATA_1M_CACHE[key_1m], start_date


def run_backtest(
    *,
    strategy_name: str,
    symbol: str,
    interval: str,
    start: str,
    end: str,
    strategy_params: Optional[Dict[str, Any]] = None,
    initial_equity: float = 50_000.0,
    risk_per_trade: float = 0.01,
    max_contracts: int = 50,
    engine_settings: Optional[BacktestEngineSettings] = None,
) -> Dict[str, Any]:
    """Run a single backtest and return the simulator result.

    If `engine_settings` is None, falls back to the UI defaults for this strategy.
    """
    load_strategies()
    if strategy_name not in STRATEGIES:
        raise ValueError(f"Unknown strategy '{strategy_name}'. Available: {list(STRATEGIES)}")
    strat_cls = STRATEGIES[strategy_name]
    contract_id = SYMBOL_CONTRACTS[symbol]
    specs = _contract_backtest_specs(symbol)

    if engine_settings is None:
        engine_settings = ui_default_engine_settings(strategy_name)

    original_start = _normalize_backtest_datetime(start)
    end_date = _normalize_backtest_datetime(end)
    warmup = STRATEGY_WARMUP_BARS.get(strategy_name, DEFAULT_WARMUP_BARS)

    data, data_1m, _ = _load_data(symbol, contract_id, interval,
                                  original_start, end_date, warmup)

    strat = strat_cls()
    params = dict(strat_cls.default_params)
    if strategy_params:
        params.update(strategy_params)
    params["tick_size"] = specs["tick_size"]

    simulator_settings = strat.get_simulator_settings(params)
    blackout_windows = _build_blackout_windows(engine_settings)
    annotated = _annotate_blackout_flags(data, blackout_windows)
    signals = strat.generate_signals(annotated, params)

    sliced, mask = _slice_from_start(data, original_start)
    sliced_signals: Dict[str, Any] = {}
    for k, v in signals.items():
        if isinstance(v, pd.Series):
            sliced_signals[k] = v.loc[mask]
        elif isinstance(v, pd.DataFrame):
            sliced_signals[k] = v.loc[mask]
        else:
            sliced_signals[k] = v

    data_1m_sliced, _ = _slice_from_start(data_1m, original_start)

    cfg = SimulatorConfig(
        initial_equity=initial_equity,
        risk_per_trade=risk_per_trade,
        max_contracts=max_contracts,
        tick_size=specs["tick_size"],
        tick_value=specs["tick_value"],
        point_value=specs["point_value"],
        fee_per_trade=specs["fee_per_trade"],
        auto_close_enabled=engine_settings.auto_close_enabled,
        auto_close_hour=engine_settings.auto_close_hour,
        auto_close_minute=engine_settings.auto_close_minute,
        blackout_windows=blackout_windows,
        cooldown_bars=int(sliced_signals.get("cooldown_bars",
                                             params.get("cooldown_bars", 0))),
        tp1_execution_mode=str(simulator_settings.get("tp1_execution_mode", "touch")),
        tp1_partial_pct=float(simulator_settings.get("tp1_partial_pct", 0.25)),
        tp2_partial_pct=float(simulator_settings.get("tp2_partial_pct", 0.25)),
        ema_exit_after_tp1_only=bool(simulator_settings.get("ema_exit_after_tp1_only", False)),
        no_sl_after_tp1=bool(simulator_settings.get("no_sl_after_tp1", False)),
        tp1_full_exit=bool(simulator_settings.get("tp1_full_exit", False)),
        inverse_canal_exit=bool(simulator_settings.get("inverse_canal_exit", False)),
        canal_exit_mode=str(simulator_settings.get("canal_exit_mode", "break_hma")),
        block_loss_canal_exit_before_tp1=bool(
            simulator_settings.get("block_loss_canal_exit_before_tp1", False)
        ),
        close_partial_min_rr=float(simulator_settings.get("close_partial_min_rr", 0.0)),
        one_trade_per_setup_window=bool(
            simulator_settings.get("one_trade_per_setup_window", False)
        ),
        final_exit_pct=float(simulator_settings.get("final_exit_pct", 0.0)),
        final_exit_min_rr=float(simulator_settings.get("final_exit_min_rr", 0.0)),
        move_to_be_on_fast_hma_cross=bool(
            simulator_settings.get("move_to_be_on_fast_hma_cross", False)
        ),
        move_to_be_on_rejected_exit=bool(
            simulator_settings.get("move_to_be_on_rejected_exit", False)
        ),
        early_exit_fired_mode=str(
            simulator_settings.get("early_exit_fired_mode", "off")
        ),
        tp_mode_fast_hma_hw=bool(simulator_settings.get("tp_mode_fast_hma_hw", True)),
        tp_mode_slow_hma_cross=bool(
            simulator_settings.get("tp_mode_slow_hma_cross", False)
        ),
        report_tp_if_mfi_ok=bool(simulator_settings.get("report_tp_if_mfi_ok", False)),
        daily_win_limit_enabled=engine_settings.daily_win_limit_enabled,
        daily_win_limit=engine_settings.daily_win_limit,
        daily_loss_limit_enabled=engine_settings.daily_loss_limit_enabled,
        daily_loss_limit=engine_settings.daily_loss_limit,
        daily_limit_mode=engine_settings.daily_limit_mode,
    )

    return simulate_strategy(
        data=sliced,
        data_1m=data_1m_sliced,
        signals=sliced_signals,
        config=cfg,
        ema_main=sliced_signals["ema_main"],
        ema_secondary=sliced_signals["ema_secondary"],
    )


def summarize(result: Dict[str, Any]) -> Dict[str, Any]:
    """Compact metrics summary from a `simulate()` result.

    Note on DD: `max_dd_$` and `max_dd_%` are tracked independently inside the
    simulator (see `src/engine/simulator.py:1838-1850`). They may correspond to
    different `(peak, trough)` pairs once equity grows past the starting
    capital. **Always compare DD budgets in $ via `max_dd_$`** — the % can be
    smaller while the $ is larger (e.g. a $3.3k drop on a $115k peak = 2.87%
    but the worst $ DD; vs a $1.8k drop on a $54k peak = 3.33% but smaller $).
    """
    m = result["metrics"]
    trades = result["trades"]
    active = [t for t in trades if not t.get("excluded", False)]
    net = sum(t["pnl"] for t in active)
    wins = [t for t in active if t["pnl"] > 0]
    losses = [t for t in active if t["pnl"] < 0]
    avg_win = (sum(t["pnl"] for t in wins) / len(wins)) if wins else 0.0
    avg_loss = (sum(t["pnl"] for t in losses) / len(losses)) if losses else 0.0
    gross_win = sum(t["pnl"] for t in wins)
    gross_loss = -sum(t["pnl"] for t in losses)
    pf = (gross_win / gross_loss) if gross_loss > 0 else float("inf")
    return {
        "net_pnl": round(net, 2),
        "trades": int(m["total_trades"]),
        "win_rate": round(m["win_rate"], 1),
        "sl_rate": round(m.get("sl_rate", 0.0), 1),
        "be_rate": round(m.get("be_rate", 0.0), 1),
        "loss_other_rate": round(m.get("loss_other_rate", 0.0), 1),
        "max_dd_$": round(m["max_drawdown_dollars"], 2),
        "max_dd_%": round(m["max_drawdown"], 2),
        "profit_factor": round(pf, 2) if pf != float("inf") else None,
        "avg_win": round(avg_win, 2),
        "avg_loss": round(avg_loss, 2),
        "sharpe": round(m.get("sharpe_ratio", 0.0), 2),
    }


def fmt_summary(s: Dict[str, Any]) -> str:
    return (
        f"PnL=${s['net_pnl']:>9,.0f} | DD=${s['max_dd_$']:>6,.0f} | "
        f"N={s['trades']:>4} | WR={s['win_rate']:>5.1f}% | "
        f"SL={s.get('sl_rate', 0):>4.1f}% | BE={s.get('be_rate', 0):>4.1f}% | "
        f"PF={s['profit_factor']} | "
        f"AW=${s['avg_win']:>6,.0f} | AL=${s['avg_loss']:>6,.0f}"
    )


def bench(label: str, **kwargs) -> Dict[str, Any]:
    """One-liner: run + summarize + print + return summary."""
    t0 = time.time()
    r = run_backtest(**kwargs)
    s = summarize(r)
    s["label"] = label
    s["elapsed_s"] = round(time.time() - t0, 1)
    print(f"{label:<60s} {fmt_summary(s)}  ({s['elapsed_s']}s)")
    return s
