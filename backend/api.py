import hashlib
import json
import logging
import sys
import os
import inspect
from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from typing import Dict, Any, List, Optional

import pandas as pd
import numpy as np
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, field_validator

# Configure module logger
logger = logging.getLogger(__name__)

# Add src to path to import strategies
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.strategies.base import Strategy
from src.data.market_store import MarketDataStore
from src.engine.simulator import BlackoutWindow, SimulatorConfig, simulate as simulate_strategy

router = APIRouter()
market_store = MarketDataStore()

# --- Cache ---
DATA_CACHE = {
    "params": None,
    "data": None,
    "original_start_date": None
}

# Signal cache for auto-update resimulation.
# Stores the expensive signal generation output so that changes to risk/engine
# params only require re-running the simulator (fast path).
SIGNAL_CACHE: Dict[str, Any] = {
    "key": None,          # (strategy, symbol, interval, start, end, params_hash)
    "sliced_data": None,
    "sliced_signals": None,
    "data_1m": None,
    "specs": None,
    "simulator_settings": None,
    "full_debug": None,
    "original_start_date": None,
    "end_date": None,
    "strategy_name": None,
    "symbol": None,
    "blackout_signature": None,
}

# --- Strategy warmup bars ---
# Bars required for FULL indicator convergence (not just first value).
# Formula: max(chain_depth) + 4 × max(EMA/rolling period) + safety margin.
# EMA(n) converges to 99% accuracy after ~4n bars from first valid value.
STRATEGY_WARMUP_BARS = {
    "EMABreakOsc": 250,     # EMA(30)→100 + MFI(35)+cloud(35)→112 + margin
    "EMA9Scalp": 150,       # EMA(7)→28 + MFI(35)+smooth(6)+cloud→76 + oscillator margin
    "UTBotAlligatorST": 120, # SMMA(13)+offset(8)→~60 + ATR(10) + margin
    "HMAOsci": 250,         # EMA(7)→28 + HMA(84)→135 + MFI(35)→41 + margin
    "HMASSLOsci": 250,          # EMA(7)→28 + HMA(84)→135 + EMA(60) SSL rangema→240 + margin
    "EMABreakHMASSLOsc": 250,  # EMA(13)→52 + EMA(60) SSL rangema→240 + margin
    "RobReversal": 150,         # EMA(13)→52 + MFI(35)+cloud(35)→112 + margin
}
DEFAULT_WARMUP_BARS = 200
BACKTEST_TZ = "Europe/Brussels"

# --- Models ---

class BacktestRequest(BaseModel):
    """Request model for backtest with validation."""
    strategy_name: str = Field(..., min_length=1, description="Name of the strategy to run")
    symbol: str = Field(..., min_length=1, description="Symbol (e.g. MNQ, MES)")
    interval: str = Field(default="15m", pattern="^(1m|2m|3m|5m|7m|15m)$", description="Data interval")
    start_datetime: str = Field(..., description="Start datetime (ISO format YYYY-MM-DDTHH:mm)")
    end_datetime: str = Field(..., description="End datetime (ISO format YYYY-MM-DDTHH:mm)")
    params: Dict[str, Any] = Field(default_factory=dict, description="Strategy parameters")

    # Risk Management with validation
    initial_equity: float = Field(default=50000.0, ge=1000, le=10000000, description="Initial equity")
    risk_per_trade: float = Field(default=0.01, ge=0.001, le=0.1, description="Risk per trade (0.01 = 1%)")

    # Trade filters
    max_contracts: int = Field(default=50, ge=1, le=1000, description="Maximum contracts per position")
    block_market_open: bool = Field(default=False, description="Deprecated legacy flag kept for backward compatibility")
    engine_settings: "BacktestEngineSettings" = Field(default_factory=lambda: BacktestEngineSettings())

    @field_validator('params')
    @classmethod
    def validate_params(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        """Validate strategy parameters are within reasonable bounds."""
        for key, value in v.items():
            if isinstance(value, (int, float)):
                if value < -10000 or value > 10000:
                    raise ValueError(f"Parameter '{key}' value {value} is out of reasonable bounds (-10000 to 10000)")
        return v

class Trade(BaseModel):
    entry_time: str
    entry_execution_time: Optional[str] = None
    exit_time: str
    exit_execution_time: Optional[str] = None
    side: str
    entry_price: float
    exit_price: float
    pnl: float
    gross_pnl: float
    fees: float
    size: float
    pnl_pct: float
    status: str
    session: str # Asia, UK, US
    legs: List["TradeLeg"] = Field(default_factory=list)
    excluded: bool = False  # True if trade was taken after daily limit reached
    source: Optional[str] = None  # "1" or "2" in multi-backtest mode


class TradeLeg(BaseModel):
    entry_time: str
    entry_execution_time: Optional[str] = None
    exit_time: str
    exit_execution_time: Optional[str] = None
    side: str
    entry_price: float
    exit_price: float
    pnl: float
    gross_pnl: float
    fees: float
    size: float
    status: str


class BlackoutWindowSettings(BaseModel):
    active: bool = False
    start_hour: int = Field(default=0, ge=0, le=23)
    start_minute: int = Field(default=0, ge=0, le=59)
    end_hour: int = Field(default=0, ge=0, le=23)
    end_minute: int = Field(default=0, ge=0, le=59)


class BacktestEngineSettings(BaseModel):
    auto_close_enabled: bool = True
    auto_close_hour: int = Field(default=21, ge=0, le=23)
    auto_close_minute: int = Field(default=0, ge=0, le=59)
    blackout_windows: List[BlackoutWindowSettings] = Field(
        default_factory=lambda: [
            BlackoutWindowSettings(active=False, start_hour=8, start_minute=0, end_hour=8, end_minute=5),
            BlackoutWindowSettings(active=True, start_hour=11, start_minute=0, end_hour=13, end_minute=0),
            BlackoutWindowSettings(active=False, start_hour=14, start_minute=30, end_hour=14, end_minute=35),
            BlackoutWindowSettings(active=True, start_hour=15, start_minute=30, end_hour=21, end_minute=0),
            BlackoutWindowSettings(active=True, start_hour=21, start_minute=0, end_hour=23, end_minute=0),
            BlackoutWindowSettings(active=False, start_hour=23, start_minute=0, end_hour=23, end_minute=5),
        ]
    )
    debug: bool = False
    daily_win_limit_enabled: bool = False
    daily_win_limit: float = Field(default=500.0, ge=0)
    daily_loss_limit_enabled: bool = False
    daily_loss_limit: float = Field(default=700.0, ge=0)

def get_session(dt_str: str) -> str:
    """Determine trading session from a timestamp string.

    Session boundaries are defined in *reference* Brussels time (= when
    Brussels–US/Eastern difference is the standard 6 h).  During the DST
    misalignment periods (~3 weeks in March, ~1 week in Oct/Nov) the offset
    is automatically applied so that sessions shift with the market.

    Reference boundaries:
        Asia  00:00 – 08:59
        UK    09:00 – 15:29
        US    15:30 – end of day
    """
    try:
        dt = pd.to_datetime(dt_str)
        if pd.isna(dt):
            return "Unknown"

        if dt.tzinfo is None:
            dt = dt.tz_localize(BACKTEST_TZ)

        from src.engine.simulator import _to_ref_minutes
        ref = _to_ref_minutes(dt)

        if ref < 540:
            return "Asia"
        if ref < 930:
            return "UK"
        return "US"
    except Exception as e:
        logger.warning(f"Failed to parse session from timestamp '{dt_str}': {e}")
        return "Unknown"

class BacktestResult(BaseModel):
    metrics: Dict[str, Any]
    trades: List[Trade]
    equity_curve: List[Dict[str, Any]]
    daily_limits_hit: Dict[str, str] = Field(default_factory=dict)  # date -> "win"|"loss"
    data_source_used: Optional[str] = None  # "local", "cache", or "api"
    debug_file: Optional[str] = None


Trade.model_rebuild()
BacktestRequest.model_rebuild()

class Contract(BaseModel):
    id: str
    name: str
    description: str

# --- Registry & Dynamic Loading ---
STRATEGIES = {}

def load_strategies():
    """Dynamically load all strategies from src/strategies"""
    global STRATEGIES
    STRATEGIES = {}
    
    strategies_path = os.path.join(os.path.dirname(__file__), '..', 'src', 'strategies')
    sys.path.append(strategies_path)
    
    # Iterate over all files in the strategies directory
    from src.strategies.base import Strategy
    import importlib.util

    logger.info(f"Loading strategies from {strategies_path}...")

    for file_name in os.listdir(strategies_path):
        if file_name.endswith(".py") and file_name != "__init__.py" and file_name != "base.py" and file_name != "indicators.py":
            module_name = file_name[:-3]
            file_path = os.path.join(strategies_path, file_name)
            
            try:
                # Dynamic import
                spec = importlib.util.spec_from_file_location(f"src.strategies.{module_name}", file_path)
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    sys.modules[f"src.strategies.{module_name}"] = module
                    spec.loader.exec_module(module)
                    
                    # Inspect for Strategy subclasses
                    for name, obj in inspect.getmembers(module):
                        if inspect.isclass(obj) and issubclass(obj, Strategy) and obj is not Strategy:
                            STRATEGIES[name] = obj
                            logger.info(f"Registered strategy: {name}")
            except Exception as e:
                logger.error(f"Failed to load strategy {file_name}: {e}")

# Initial Load
load_strategies()

# --- Endpoints ---

@router.get("/strategies")
def get_strategies():
    # Reload to pick up new files without restart (optional, but good for dev)
    # load_strategies() # Uncomment for hot-reloading on every request (slower)
    
    results = []
    for name, cls in STRATEGIES.items():
        defaults = getattr(cls, 'default_params', {})
        results.append({
            "name": name,
            "description": cls.__doc__.strip() if cls.__doc__ else "No description",
            "default_params": defaults
        })
    return results

@router.get("/available-data")
def get_available_data():
    """Return available symbols, timeframes, and date ranges from local data store."""
    datasets = market_store.list_datasets()
    result = []
    for ds in datasets:
        # Calculate min start datetime per strategy considering warmup buffer
        min_starts = {}
        for strat_name in STRATEGIES:
            warmup_bars = STRATEGY_WARMUP_BARS.get(strat_name, DEFAULT_WARMUP_BARS)
            min_starts[strat_name] = {}
            for tf in ds.get("timeframes", []):
                # Convert warmup bars to calendar time, same formula as /backtest
                map_min = {"1m": 1, "2m": 2, "3m": 3, "5m": 5, "7m": 7, "15m": 15}
                mpb = map_min.get(tf, 15)
                trading_mins = warmup_bars * mpb
                t_days = trading_mins / (23 * 60)
                cal_days = max(2, int(t_days * 7 / 5) + 3)
                ds_start = pd.Timestamp(ds["start_date"])
                min_start = ds_start + timedelta(days=cal_days)
                min_starts[strat_name][tf] = min_start.isoformat()

        result.append({
            "symbol": ds["symbol"],
            "contract_id": ds.get("contract_id"),
            "timeframes": ds.get("timeframes", []),
            "start_date": ds["start_date"],
            "end_date": ds["end_date"],
            "bar_count_1m": ds.get("bar_count_1m", 0),
            "min_start_per_strategy": min_starts,
        })
    return result

# --- Constants ---
# Fee Map (Round Turn) based on user input
# Fee Map (Round Turn) based on user input
FEES_MAP = {
    "ES": 2.80, "MES": 0.74,
    "NQ": 2.80, "MNQ": 0.74,
    "RTY": 2.80, "M2K": 0.74,
    "YM": 2.80, "MYM": 0.74, # Dow
    "NKD": 4.34, # Nikkei
    "MBT": 2.34, # Micro BTC
    "MET": 0.24, # Micro ETH
    "GC": 3.24, "MGC": 1.24, # Gold
    "CL": 3.04, "MCL": 1.04, # Crude
    "SI": 3.24, "SIL": 2.04, # Silver
    "HG": 3.24, # Copper
    "6A": 3.24, "M6A": 0.52, # AUD
    "6E": 3.24, "M6E": 0.52, # EUR
    "6B": 3.24, "M6B": 0.52, # GBP
}

# Contract Specs from Architecture.md
# Tick Size, Tick Value
CONTRACT_SPECS = {
    "ES":  {"tick_size": 0.25, "tick_value": 12.50},
    "MES": {"tick_size": 0.25, "tick_value": 1.25},
    "NQ":  {"tick_size": 0.25, "tick_value": 5.00},
    "MNQ": {"tick_size": 0.25, "tick_value": 0.50},
    "RTY": {"tick_size": 0.10, "tick_value": 5.00}, # Russell 2000
    "M2K": {"tick_size": 0.10, "tick_value": 0.50},
    "YM":  {"tick_size": 1.00, "tick_value": 5.00},
    "MYM": {"tick_size": 1.00, "tick_value": 0.50},
    "GC":  {"tick_size": 0.10, "tick_value": 10.00},
    "MGC": {"tick_size": 0.10, "tick_value": 1.00},
    "CL":  {"tick_size": 0.01, "tick_value": 10.00},
    "MCL": {"tick_size": 0.01, "tick_value": 1.00},
    "MBT": {"tick_size": 5.00, "tick_value": 0.50},
}


def _normalize_backtest_datetime(value: str) -> pd.Timestamp:
    ts = pd.to_datetime(value)
    if ts.tzinfo is None:
        return ts.tz_localize(BACKTEST_TZ)
    return ts.tz_convert(BACKTEST_TZ)


def _slice_from_start(data: pd.DataFrame, start_ts: pd.Timestamp) -> tuple[pd.DataFrame, pd.Series]:
    aligned_start = pd.Timestamp(start_ts)
    if data.index.tz is not None:
        if aligned_start.tzinfo is None:
            aligned_start = aligned_start.tz_localize(data.index.tz)
        else:
            aligned_start = aligned_start.tz_convert(data.index.tz)
    elif aligned_start.tzinfo is not None:
        aligned_start = aligned_start.tz_localize(None)

    mask = data.index >= aligned_start
    return data.loc[mask], mask


def _build_blackout_windows(engine_settings: BacktestEngineSettings) -> List[BlackoutWindow]:
    windows: List[BlackoutWindow] = []
    for window in engine_settings.blackout_windows:
        windows.append(
            BlackoutWindow(
                active=window.active,
                start_hour=window.start_hour,
                start_minute=window.start_minute,
                end_hour=window.end_hour,
                end_minute=window.end_minute,
            )
        )
    return windows


def _annotate_blackout_flags(
    data: pd.DataFrame,
    blackout_windows: List[BlackoutWindow],
) -> pd.DataFrame:
    """Attach per-bar blackout flags for strategy state machines.

    Matches Pine/simulator semantics: blackout is evaluated on the bar close
    timestamp, not the bar open timestamp.
    """
    annotated = data.copy()

    if not blackout_windows or not any(window.active for window in blackout_windows):
        annotated["is_blackout"] = False
        return annotated

    from src.engine.simulator import _is_blackout

    inferred_bar_delta = (
        annotated.index[1] - annotated.index[0]
        if len(annotated.index) > 1
        else pd.Timedelta(minutes=1)
    )
    close_times = [
        annotated.index[i + 1] if i + 1 < len(annotated.index) else annotated.index[i] + inferred_bar_delta
        for i in range(len(annotated.index))
    ]
    annotated["is_blackout"] = [_is_blackout(pd.Timestamp(ts), blackout_windows) for ts in close_times]
    return annotated


def _blackout_signature(engine_settings: BacktestEngineSettings) -> tuple:
    return tuple(
        (
            bool(window.active),
            int(window.start_hour),
            int(window.start_minute),
            int(window.end_hour),
            int(window.end_minute),
        )
        for window in engine_settings.blackout_windows
    )


def _contract_backtest_specs(symbol: str) -> Dict[str, float]:
    tick_size = 0.25
    tick_value = 12.5
    point_value = tick_value / tick_size
    fee_per_trade = 0.0

    if symbol in CONTRACT_SPECS:
        spec = CONTRACT_SPECS[symbol]
        tick_size = spec["tick_size"]
        tick_value = spec["tick_value"]
        point_value = tick_value / tick_size if tick_size > 0 else 1.0

    if symbol in FEES_MAP:
        fee_per_trade = FEES_MAP[symbol]

    return {
        "tick_size": tick_size,
        "tick_value": tick_value,
        "point_value": point_value,
        "fee_per_trade": fee_per_trade,
    }


def _append_debug_event(df: pd.DataFrame, ts_value: str, column: str, event: str) -> None:
    if column not in df.columns:
        df[column] = ""

    ts = pd.Timestamp(ts_value)
    if df.index.tz is not None:
        if ts.tzinfo is None:
            ts = ts.tz_localize(df.index.tz)
        else:
            ts = ts.tz_convert(df.index.tz)
    elif ts.tzinfo is not None:
        ts = ts.tz_localize(None)

    if ts not in df.index:
        return

    current = df.at[ts, column]
    if current:
        df.at[ts, column] = f"{current} | {event}"
    else:
        df.at[ts, column] = event


def _write_debug_export(
    req: "BacktestRequest",
    debug_frame: Optional[pd.DataFrame],
    trades: List[Dict[str, Any]],
    original_start_date: Optional[pd.Timestamp] = None,
    end_date: Optional[pd.Timestamp] = None,
) -> Optional[str]:
    if debug_frame is None or debug_frame.empty:
        return None

    export = debug_frame.copy()
    export["used_for_backtest"] = 1
    export["in_requested_range"] = 1

    if original_start_date is not None:
        start_ts = pd.Timestamp(original_start_date)
        if export.index.tz is not None:
            if start_ts.tzinfo is None:
                start_ts = start_ts.tz_localize("UTC").tz_convert(export.index.tz)
            else:
                start_ts = start_ts.tz_convert(export.index.tz)
        elif start_ts.tzinfo is not None:
            start_ts = start_ts.tz_localize(None)
        export["in_requested_range"] = (export.index >= start_ts).astype(int)

    if end_date is not None:
        end_ts = pd.Timestamp(end_date)
        if export.index.tz is not None:
            if end_ts.tzinfo is None:
                end_ts = end_ts.tz_localize("UTC").tz_convert(export.index.tz)
            else:
                end_ts = end_ts.tz_convert(export.index.tz)
        elif end_ts.tzinfo is not None:
            end_ts = end_ts.tz_localize(None)
        export["in_requested_range"] = (
            export["in_requested_range"].astype(bool) & (export.index <= end_ts)
        ).astype(int)

    export["trade_entries"] = ""
    export["trade_exits"] = ""

    for trade in trades:
        _append_debug_event(
            export,
            trade["entry_time"],
            "trade_entries",
            (
                f"{trade['side']} entry @ {trade['entry_price']:.2f}"
                f" (exec {trade.get('entry_execution_time') or trade['entry_time']})"
            ),
        )
        for leg in trade.get("legs", []):
            _append_debug_event(
                export,
                leg["exit_time"],
                "trade_exits",
                (
                    f"{leg['status']} size={leg['size']:.0f} exit={leg['exit_price']:.2f}"
                    f" (exec {leg.get('exit_execution_time') or leg['exit_time']})"
                ),
            )

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = Path("debug") / "backtests" / req.strategy_name
    output_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{req.symbol}_{req.interval}_{stamp}.csv"
    output_path = output_dir / filename
    export.to_csv(output_path, index_label="bar_time")
    return str(output_path)


def _make_signal_cache_key(strategy_name: str, symbol: str, interval: str,
                           start: str, end: str, params: Dict[str, Any]) -> str:
    """Build a deterministic cache key for signal generation results."""
    # Exclude params that only affect simulation, not signal generation
    sig_params = {k: v for k, v in sorted(params.items())
                  if k not in ("tp1_partial_pct", "tp2_partial_pct", "tick_size")}
    raw = f"{strategy_name}|{symbol}|{interval}|{start}|{end}|{json.dumps(sig_params, sort_keys=True, default=str)}"
    return hashlib.md5(raw.encode()).hexdigest()


def _run_simulator_backtest(
    req: "BacktestRequest",
    contract_id: str,
    strategy_instance: Strategy,
    params: Dict[str, Any],
    data: pd.DataFrame,
    start_date: pd.Timestamp,
    end_date: pd.Timestamp,
    original_start_date: pd.Timestamp,
) -> Dict[str, Any]:
    specs = _contract_backtest_specs(req.symbol)
    params["tick_size"] = specs["tick_size"]
    engine_settings = req.engine_settings
    simulator_settings = strategy_instance.get_simulator_settings(params)
    blackout_windows = _build_blackout_windows(engine_settings)
    signal_data = _annotate_blackout_flags(data, blackout_windows)

    try:
        signals = strategy_instance.generate_signals(signal_data, params)
        if not isinstance(signals, dict):
            raise ValueError("Simulator-backed strategies must return a signal dictionary")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Strategy execution error: {str(e)}") from e

    sliced_data, mask = _slice_from_start(data, original_start_date)
    if sliced_data.empty:
        raise HTTPException(status_code=400, detail="Data empty after warmup slicing. Fetch more history?")

    sliced_signals: Dict[str, Any] = {}
    for key, value in signals.items():
        if isinstance(value, pd.Series):
            sliced_signals[key] = value.loc[mask]
        elif isinstance(value, pd.DataFrame):
            sliced_signals[key] = value.loc[mask]
        else:
            sliced_signals[key] = value

    data_1m = market_store.load_bars(contract_id, start_date, end_date, "1m")
    data_1m, _ = _slice_from_start(data_1m, original_start_date)

    # Populate signal cache for auto-update resimulation
    cache_key = _make_signal_cache_key(
        req.strategy_name, req.symbol, req.interval,
        req.start_datetime, req.end_datetime, params,
    )
    SIGNAL_CACHE["key"] = cache_key
    SIGNAL_CACHE["sliced_data"] = sliced_data
    SIGNAL_CACHE["sliced_signals"] = sliced_signals
    SIGNAL_CACHE["data_1m"] = data_1m
    SIGNAL_CACHE["specs"] = specs
    SIGNAL_CACHE["simulator_settings"] = simulator_settings
    SIGNAL_CACHE["full_debug"] = signals.get("debug_frame")
    SIGNAL_CACHE["original_start_date"] = original_start_date
    SIGNAL_CACHE["end_date"] = end_date
    SIGNAL_CACHE["strategy_name"] = req.strategy_name
    SIGNAL_CACHE["symbol"] = req.symbol
    SIGNAL_CACHE["blackout_signature"] = _blackout_signature(engine_settings)
    SIGNAL_CACHE["params"] = params.copy()

    config = SimulatorConfig(
        initial_equity=req.initial_equity,
        risk_per_trade=req.risk_per_trade,
        max_contracts=req.max_contracts,
        tick_size=specs["tick_size"],
        tick_value=specs["tick_value"],
        point_value=specs["point_value"],
        fee_per_trade=specs["fee_per_trade"],
        auto_close_enabled=engine_settings.auto_close_enabled,
        auto_close_hour=engine_settings.auto_close_hour,
        auto_close_minute=engine_settings.auto_close_minute,
        blackout_windows=blackout_windows,
        cooldown_bars=int(sliced_signals.get("cooldown_bars", params.get("cooldown_bars", 0))),
        tp1_execution_mode=str(simulator_settings.get("tp1_execution_mode", "touch")),
        tp1_partial_pct=float(simulator_settings.get("tp1_partial_pct", 0.25)),
        tp2_partial_pct=float(simulator_settings.get("tp2_partial_pct", 0.25)),
        ema_exit_after_tp1_only=bool(simulator_settings.get("ema_exit_after_tp1_only", False)),
        no_sl_after_tp1=bool(simulator_settings.get("no_sl_after_tp1", False)),
        tp1_full_exit=bool(simulator_settings.get("tp1_full_exit", False)),
        inverse_canal_exit=bool(simulator_settings.get("inverse_canal_exit", False)),
        canal_exit_mode=str(simulator_settings.get("canal_exit_mode", "break_hma")),
        daily_win_limit_enabled=engine_settings.daily_win_limit_enabled,
        daily_win_limit=engine_settings.daily_win_limit,
        daily_loss_limit_enabled=engine_settings.daily_loss_limit_enabled,
        daily_loss_limit=engine_settings.daily_loss_limit,
    )

    try:
        result = simulate_strategy(
            data=sliced_data,
            data_1m=data_1m,
            signals=sliced_signals,
            config=config,
            ema_main=sliced_signals["ema_main"],
            ema_secondary=sliced_signals["ema_secondary"],
        )
        if engine_settings.debug:
            # Slice debug_frame to only include bars from backtest start onward
            # (warmup bars are not useful for debugging — indicators are already converged)
            full_debug = signals.get("debug_frame")
            if full_debug is not None and not full_debug.empty:
                sliced_debug, _ = _slice_from_start(full_debug, original_start_date)
            else:
                sliced_debug = full_debug
            result["debug_file"] = _write_debug_export(
                req=req,
                debug_frame=sliced_debug,
                trades=result["trades"],
                original_start_date=original_start_date,
                end_date=end_date,
            )
        else:
            result["debug_file"] = None
        result["data_source_used"] = "local"
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Simulation error: {str(e)}") from e

@router.post("/backtest", response_model=BacktestResult)
def run_backtest(req: BacktestRequest):
    # Reload strategies to ensure code changes are picked up dynamically
    load_strategies()

    if req.strategy_name not in STRATEGIES:
        raise HTTPException(status_code=404, detail="Strategy not found")

    # 1. Parse datetimes
    try:
        original_start_date = _normalize_backtest_datetime(req.start_datetime)
        end_date = _normalize_backtest_datetime(req.end_datetime)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid datetime format: {e}")

    # 2. Resolve contract_id from symbol
    from src.data.market_store import SYMBOL_CONTRACTS
    contract_id = SYMBOL_CONTRACTS.get(req.symbol)
    if not contract_id:
        raise HTTPException(status_code=400, detail=f"Unknown symbol: {req.symbol}")

    # 3. Warmup: load enough bars BEFORE backtest start for full indicator convergence.
    # Each strategy specifies how many bars it needs in STRATEGY_WARMUP_BARS.
    # Convert bars to calendar days, accounting for weekends and overnight closes.
    # Futures trade ~23h/day, 5 days/week → we need 7/5 calendar days per trading day.
    warmup_bars = STRATEGY_WARMUP_BARS.get(req.strategy_name, DEFAULT_WARMUP_BARS)
    map_min = {"1m": 1, "2m": 2, "3m": 3, "5m": 5, "7m": 7, "15m": 15}
    minutes_per_bar = map_min.get(req.interval, 15)
    trading_minutes_needed = warmup_bars * minutes_per_bar
    # 23h trading per day, 5 days per 7 calendar days, + 3 days buffer for holidays
    trading_days = trading_minutes_needed / (23 * 60)
    calendar_days = max(2, int(trading_days * 7 / 5) + 3)
    start_date = original_start_date - timedelta(days=calendar_days)

    # Clamp to dataset start — don't request data before what's available
    ds_meta = market_store.get_dataset_by_symbol(req.symbol)
    if ds_meta:
        ds_start = pd.Timestamp(ds_meta["start_date"])
        if ds_start.tzinfo is None:
            ds_start = ds_start.tz_localize(BACKTEST_TZ)
        if start_date < ds_start:
            start_date = ds_start
    logger.info(f"Warmup: {warmup_bars} bars for {req.strategy_name}. Adjusted start: {start_date}")

    # 4. Load data from local store
    try:
        data = pd.DataFrame()

        # Check in-memory cache
        current_params = (req.symbol, req.interval, str(start_date), str(end_date))
        if DATA_CACHE["params"] == current_params and DATA_CACHE["data"] is not None:
            logger.info(f"Using cached data for {current_params}")
            data = DATA_CACHE["data"].copy()
        else:
            # Load from local CSV files
            ds = market_store.get_dataset_by_symbol(req.symbol)
            if ds is None:
                raise HTTPException(status_code=400, detail=f"No local data available for {req.symbol}")

            logger.info(f"Loading local data for {req.symbol}, timeframe={req.interval}, range={start_date} to {end_date}")
            data = market_store.load_bars(contract_id, start_date, end_date, req.interval)

            # Update cache
            DATA_CACHE["params"] = current_params
            DATA_CACHE["data"] = data.copy()
            DATA_CACHE["original_start_date"] = original_start_date

        if data.empty:
            raise HTTPException(status_code=400, detail=f"No data found for {req.symbol} in the requested date range")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Data load error: {str(e)}")

    # 2. Run Strategy on FULL DATA (including warmup)
    StrategyClass = STRATEGIES[req.strategy_name]
    strategy_instance = StrategyClass()
    params = strategy_instance.default_params.copy()
    params.update(req.params)

    contract_specs = _contract_backtest_specs(req.symbol)
    params["tick_size"] = contract_specs["tick_size"]

    return _run_simulator_backtest(
        req=req,
        contract_id=contract_id,
        strategy_instance=strategy_instance,
        params=params,
        data=data,
        start_date=start_date,
        end_date=end_date,
        original_start_date=original_start_date,
    )


# ---------------------------------------------------------------------------
# Auto-update resimulation endpoint — reuses cached signals, only re-runs
# the simulator with updated risk/engine/partial params.
# ---------------------------------------------------------------------------

class ResimulateRequest(BaseModel):
    """Lightweight request for re-running only the simulator."""
    # Risk
    initial_equity: float = Field(default=50000.0, ge=1000, le=10000000)
    risk_per_trade: float = Field(default=0.01, ge=0.001, le=0.1)
    max_contracts: int = Field(default=50, ge=1, le=1000)
    # Strategy params that only affect simulation (TP partials, cooldown)
    params: Dict[str, Any] = Field(default_factory=dict)
    # Engine
    engine_settings: BacktestEngineSettings = Field(default_factory=lambda: BacktestEngineSettings())


@router.post("/backtest/resimulate", response_model=BacktestResult)
def resimulate(req: ResimulateRequest):
    """Re-run only the simulator using cached signals.

    This is the fast path for auto-update mode: when the user changes
    risk, engine, or partial TP parameters, we skip data loading and
    signal generation entirely and only replay the simulation.
    """
    if SIGNAL_CACHE["key"] is None or SIGNAL_CACHE["sliced_data"] is None:
        raise HTTPException(status_code=400, detail="No cached signals available. Run a full backtest first.")

    sliced_data = SIGNAL_CACHE["sliced_data"]
    sliced_signals = SIGNAL_CACHE["sliced_signals"]
    data_1m = SIGNAL_CACHE["data_1m"]
    specs = SIGNAL_CACHE["specs"]
    base_simulator_settings = SIGNAL_CACHE["simulator_settings"]
    cached_params = SIGNAL_CACHE["params"]

    # Merge override params into cached strategy params for simulator settings
    merged_params = cached_params.copy()
    merged_params.update(req.params)

    # Re-derive simulator settings with potentially updated partials
    strategy_name = SIGNAL_CACHE["strategy_name"]
    if strategy_name in STRATEGIES:
        strategy_instance = STRATEGIES[strategy_name]()
        simulator_settings = strategy_instance.get_simulator_settings(merged_params)
        blackout_sensitive = bool(getattr(strategy_instance, "blackout_sensitive", False))
    else:
        simulator_settings = base_simulator_settings
        blackout_sensitive = False

    engine_settings = req.engine_settings

    if blackout_sensitive and SIGNAL_CACHE.get("blackout_signature") != _blackout_signature(engine_settings):
        raise HTTPException(
            status_code=400,
            detail=(
                f"Blackout window changes require a full backtest for {strategy_name}. "
                "Cached resimulation is exact only when blackout windows are unchanged."
            ),
        )

    config = SimulatorConfig(
        initial_equity=req.initial_equity,
        risk_per_trade=req.risk_per_trade,
        max_contracts=req.max_contracts,
        tick_size=specs["tick_size"],
        tick_value=specs["tick_value"],
        point_value=specs["point_value"],
        fee_per_trade=specs["fee_per_trade"],
        auto_close_enabled=engine_settings.auto_close_enabled,
        auto_close_hour=engine_settings.auto_close_hour,
        auto_close_minute=engine_settings.auto_close_minute,
        blackout_windows=_build_blackout_windows(engine_settings),
        cooldown_bars=int(sliced_signals.get("cooldown_bars", merged_params.get("cooldown_bars", 0))),
        tp1_execution_mode=str(simulator_settings.get("tp1_execution_mode", "touch")),
        tp1_partial_pct=float(simulator_settings.get("tp1_partial_pct", 0.25)),
        tp2_partial_pct=float(simulator_settings.get("tp2_partial_pct", 0.25)),
        ema_exit_after_tp1_only=bool(simulator_settings.get("ema_exit_after_tp1_only", False)),
        no_sl_after_tp1=bool(simulator_settings.get("no_sl_after_tp1", False)),
        tp1_full_exit=bool(simulator_settings.get("tp1_full_exit", False)),
        inverse_canal_exit=bool(simulator_settings.get("inverse_canal_exit", False)),
        canal_exit_mode=str(simulator_settings.get("canal_exit_mode", "break_hma")),
        daily_win_limit_enabled=engine_settings.daily_win_limit_enabled,
        daily_win_limit=engine_settings.daily_win_limit,
        daily_loss_limit_enabled=engine_settings.daily_loss_limit_enabled,
        daily_loss_limit=engine_settings.daily_loss_limit,
    )

    try:
        result = simulate_strategy(
            data=sliced_data,
            data_1m=data_1m,
            signals=sliced_signals,
            config=config,
            ema_main=sliced_signals["ema_main"],
            ema_secondary=sliced_signals["ema_secondary"],
        )
        result["debug_file"] = None
        result["data_source_used"] = "cache"
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Resimulation error: {str(e)}") from e


# =============================================================================
# MULTI-BACKTEST — run two configs in parallel on the same account
# =============================================================================

class MultiBacktestConfig(BaseModel):
    """Per-slot configuration for a multi-backtest run."""
    strategy_name: str = Field(..., min_length=1)
    symbol: str = Field(..., min_length=1)
    interval: str = Field(default="15m", pattern="^(1m|2m|3m|5m|7m|15m)$")
    params: Dict[str, Any] = Field(default_factory=dict)
    risk_per_trade: float = Field(default=0.01, ge=0.001, le=0.1)
    max_contracts: int = Field(default=50, ge=1, le=1000)
    engine_settings: BacktestEngineSettings = Field(default_factory=lambda: BacktestEngineSettings())


class MultiBacktestRequest(BaseModel):
    """Request for a multi-asset or multi-strategy backtest."""
    mode: str = Field(..., pattern="^(multi_asset|multi_strat)$")
    start_datetime: str
    end_datetime: str
    initial_equity: float = Field(default=50000.0, ge=1000, le=10000000)
    configs: List[MultiBacktestConfig] = Field(..., min_length=2, max_length=2)


class MultiConfigResult(BaseModel):
    """Per-slot results within a multi-backtest response."""
    strategy_name: str
    symbol: str
    interval: str
    label: str  # e.g. "MNQ / EMABreakOsc (5m)"
    metrics: Dict[str, Any]
    trade_count: int
    blocked_count: int  # trades skipped due to shared-position lock (multi_strat only)


class MultiBacktestResult(BaseModel):
    """Combined result for a multi-backtest run."""
    mode: str
    metrics: Dict[str, Any]
    trades: List[Trade]
    equity_curve: List[Dict[str, Any]]
    daily_limits_hit: Dict[str, str] = Field(default_factory=dict)
    config_results: List[MultiConfigResult]


def _compute_combined_metrics(initial_equity: float, trades: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Compute combined backtest metrics from a merged trade list."""
    active = [t for t in trades if not t.get("excluded", False)]
    total = len(active)
    wins = sum(1 for t in active if t["pnl"] > 0)
    win_rate = wins / total * 100 if total > 0 else 0.0

    equity = initial_equity
    peak = initial_equity
    max_dd = 0.0
    sorted_active = sorted(active, key=lambda t: t["entry_time"])
    for trade in sorted_active:
        equity += trade["pnl"]
        if equity > peak:
            peak = equity
        dd = (peak - equity) / peak if peak > 0 else 0.0
        if dd > max_dd:
            max_dd = dd

    total_return = (equity - initial_equity) / initial_equity * 100 if initial_equity > 0 else 0.0
    return {
        "total_return": total_return,
        "win_rate": win_rate,
        "total_trades": total,
        "max_drawdown": max_dd * 100,
        "sharpe_ratio": 0.0,
    }


def _compute_combined_equity_curve(initial_equity: float, trades: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Build combined equity curve from merged trades sorted by entry time."""
    active = [t for t in trades if not t.get("excluded", False)]
    sorted_active = sorted(active, key=lambda t: t["entry_time"])
    curve = [{"time": "Start", "value": initial_equity}]
    equity = initial_equity
    for trade in sorted_active:
        equity += trade["pnl"]
        exit_ts = trade.get("exit_execution_time") or trade["exit_time"]
        curve.append({"time": exit_ts, "value": equity})
    return curve


def _apply_shared_position_lock(
    trades1: List[Dict[str, Any]],
    trades2: List[Dict[str, Any]],
) -> tuple[List[Dict[str, Any]], int]:
    """
    For multi_strat mode: enforce that only one trade can be open at a time
    across both strategy streams.

    Processes trades in chronological order. A trade is blocked if a trade
    from the other stream is already open (its exit_time > current entry_time).

    Returns (accepted_trades, blocked_count).
    """
    all_trades = sorted(trades1 + trades2, key=lambda t: t["entry_time"])
    accepted: List[Dict[str, Any]] = []
    blocked = 0
    last_exit_time: Optional[str] = None

    for trade in all_trades:
        entry_time = trade["entry_time"]
        exit_time = trade["exit_time"]
        if last_exit_time is None or entry_time >= last_exit_time:
            accepted.append(trade)
            last_exit_time = exit_time
        else:
            blocked += 1

    return accepted, blocked


def _run_config_for_multi(
    config: MultiBacktestConfig,
    start_datetime: str,
    end_datetime: str,
    initial_equity: float,
    source_label: str,
) -> Dict[str, Any]:
    """
    Run a single slot config through the full backtest pipeline.
    Returns the raw result dict with trades tagged with source_label.
    Raises HTTPException on any error.
    """
    if config.strategy_name not in STRATEGIES:
        raise HTTPException(status_code=404, detail=f"Strategy not found: {config.strategy_name}")

    from src.data.market_store import SYMBOL_CONTRACTS
    contract_id = SYMBOL_CONTRACTS.get(config.symbol)
    if not contract_id:
        raise HTTPException(status_code=400, detail=f"Unknown symbol: {config.symbol}")

    try:
        original_start_date = _normalize_backtest_datetime(start_datetime)
        end_date = _normalize_backtest_datetime(end_datetime)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid datetime: {e}")

    # Warmup
    warmup_bars = STRATEGY_WARMUP_BARS.get(config.strategy_name, DEFAULT_WARMUP_BARS)
    map_min = {"1m": 1, "2m": 2, "3m": 3, "5m": 5, "7m": 7, "15m": 15}
    minutes_per_bar = map_min.get(config.interval, 15)
    trading_days = (warmup_bars * minutes_per_bar) / (23 * 60)
    calendar_days = max(2, int(trading_days * 7 / 5) + 3)
    start_date = original_start_date - timedelta(days=calendar_days)

    ds_meta = market_store.get_dataset_by_symbol(config.symbol)
    if ds_meta:
        ds_start = pd.Timestamp(ds_meta["start_date"])
        if ds_start.tzinfo is None:
            ds_start = ds_start.tz_localize(BACKTEST_TZ)
        if start_date < ds_start:
            start_date = ds_start

    # Load data
    try:
        data = market_store.load_bars(contract_id, start_date, end_date, config.interval)
        if data.empty:
            raise HTTPException(status_code=400, detail=f"No data for {config.symbol} in range")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Data load error: {e}")

    StrategyClass = STRATEGIES[config.strategy_name]
    strategy_instance = StrategyClass()
    params = strategy_instance.default_params.copy()
    params.update(config.params)
    params["tick_size"] = _contract_backtest_specs(config.symbol)["tick_size"]

    # Build a BacktestRequest-like object for _run_simulator_backtest
    fake_req = SimpleNamespace(
        strategy_name=config.strategy_name,
        symbol=config.symbol,
        interval=config.interval,
        start_datetime=start_datetime,
        end_datetime=end_datetime,
        initial_equity=initial_equity,
        risk_per_trade=config.risk_per_trade,
        max_contracts=config.max_contracts,
        engine_settings=config.engine_settings,
    )

    result = _run_simulator_backtest(
        req=fake_req,
        contract_id=contract_id,
        strategy_instance=strategy_instance,
        params=params,
        data=data,
        start_date=start_date,
        end_date=end_date,
        original_start_date=original_start_date,
    )

    # Tag all trades with the source label
    for trade in result.get("trades", []):
        trade["source"] = source_label

    return result


@router.post("/backtest/multi", response_model=MultiBacktestResult)
def run_multi_backtest(req: MultiBacktestRequest):
    """
    Run two strategy/asset configs in parallel on the same account.

    multi_asset: both configs run independently; both can have open positions
                 simultaneously (different tickers).
    multi_strat: both configs run on the same ticker; only one position can
                 be open at a time across both strategies.
    """
    load_strategies()

    if req.mode == "multi_strat" and req.configs[0].symbol != req.configs[1].symbol:
        raise HTTPException(
            status_code=400,
            detail="multi_strat mode requires both configs to use the same symbol",
        )

    cfg1, cfg2 = req.configs[0], req.configs[1]
    label1 = f"{cfg1.symbol} / {cfg1.strategy_name} ({cfg1.interval})"
    label2 = f"{cfg2.symbol} / {cfg2.strategy_name} ({cfg2.interval})"

    result1 = _run_config_for_multi(cfg1, req.start_datetime, req.end_datetime, req.initial_equity, "1")
    result2 = _run_config_for_multi(cfg2, req.start_datetime, req.end_datetime, req.initial_equity, "2")

    trades1 = result1.get("trades", [])
    trades2 = result2.get("trades", [])

    if req.mode == "multi_strat":
        merged_trades, _ = _apply_shared_position_lock(trades1, trades2)
    else:
        # multi_asset: both run fully independently
        merged_trades = sorted(trades1 + trades2, key=lambda t: t["entry_time"])

    combined_metrics = _compute_combined_metrics(req.initial_equity, merged_trades)
    combined_curve = _compute_combined_equity_curve(req.initial_equity, merged_trades)

    # Per-config metrics: from their independent runs
    def _config_result(result, cfg, label, blocked):
        trades = result.get("trades", [])
        active = [t for t in trades if not t.get("excluded", False)]
        return MultiConfigResult(
            strategy_name=cfg.strategy_name,
            symbol=cfg.symbol,
            interval=cfg.interval,
            label=label,
            metrics=result.get("metrics", {}),
            trade_count=len(active),
            blocked_count=blocked,
        )

    # Count how many trades from each stream were dropped by the shared-position lock
    if req.mode == "multi_strat":
        merged_set = set(id(t) for t in merged_trades)
        blocked1 = sum(1 for t in trades1 if id(t) not in merged_set)
        blocked2 = sum(1 for t in trades2 if id(t) not in merged_set)
    else:
        blocked1 = blocked2 = 0

    config_results = [
        _config_result(result1, cfg1, label1, blocked1),
        _config_result(result2, cfg2, label2, blocked2),
    ]

    # Convert trade dicts to Trade objects for serialization
    trade_objects = []
    for t in merged_trades:
        trade_objects.append(Trade(**{k: v for k, v in t.items() if k in Trade.model_fields}))

    return MultiBacktestResult(
        mode=req.mode,
        metrics=combined_metrics,
        trades=trade_objects,
        equity_curve=combined_curve,
        config_results=config_results,
    )


# =============================================================================
# PRESETS — persistent favorites stored as JSON on disk
# =============================================================================

PRESETS_FILE = Path(__file__).resolve().parent.parent / "data" / "presets.json"


def _load_presets_from_disk() -> List[Dict[str, Any]]:
    if not PRESETS_FILE.exists():
        return []
    try:
        return json.loads(PRESETS_FILE.read_text(encoding="utf-8"))
    except Exception:
        return []


def _save_presets_to_disk(presets: List[Dict[str, Any]]) -> None:
    PRESETS_FILE.parent.mkdir(parents=True, exist_ok=True)
    PRESETS_FILE.write_text(json.dumps(presets, indent=2, default=str), encoding="utf-8")


@router.get("/presets")
def get_presets():
    return _load_presets_from_disk()


@router.post("/presets")
def create_preset(preset: Dict[str, Any]):
    presets = _load_presets_from_disk()
    presets.insert(0, preset)
    _save_presets_to_disk(presets)
    return presets


@router.delete("/presets/{preset_id}")
def delete_preset(preset_id: str):
    presets = [p for p in _load_presets_from_disk() if p.get("id") != preset_id]
    _save_presets_to_disk(presets)
    return presets


@router.put("/presets/{preset_id}/rename")
def rename_preset(preset_id: str, body: Dict[str, Any]):
    name = body.get("name", "")
    presets = _load_presets_from_disk()
    for p in presets:
        if p.get("id") == preset_id:
            p["name"] = name
            break
    _save_presets_to_disk(presets)
    return presets


# =============================================================================
# OPTIMIZATION ENDPOINTS (legacy — still uses VectorBT, to be refactored)
# =============================================================================

try:
    import vectorbt as vbt
except ModuleNotFoundError:  # pragma: no cover
    vbt = None

from concurrent.futures import ProcessPoolExecutor, as_completed
from uuid import uuid4
import itertools
from pathlib import Path

# Optimization Models
class ParameterRangeInput(BaseModel):
    """Input for a parameter range."""
    name: str
    min_value: float
    max_value: float
    step: float
    param_type: str = "float"  # "float", "int", "bool", "str_options"
    str_values: Optional[List[str]] = None  # For str_options type

class OptimizationRequest(BaseModel):
    """Request model for optimization."""
    strategy_name: str
    ticker: str = "BTC-USD"
    source: str = Field(default="Topstep", pattern="^(Yahoo|Topstep)$")
    contract_id: Optional[str] = None
    interval: str = Field(default="15m", pattern="^(1m|2m|3m|5m|7m|15m|30m|1h|4h|1d)$")
    days: int = Field(default=14, ge=1, le=365)

    # Parameters to optimize (if empty, uses strategy's param_ranges)
    parameters: List[ParameterRangeInput] = Field(default_factory=list)

    # Sessions to test
    sessions: List[str] = Field(default=["Asia", "UK", "US"])
    
    # Date Range (overrides 'days' if present)
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    
    # Topstep Live Mode
    topstep_live_mode: bool = False

    # Risk config
    initial_equity: float = Field(default=50000.0, ge=1000, le=10000000)
    risk_per_trade: float = Field(default=0.01, ge=0.001, le=0.1)

    # Trade filters
    max_contracts: int = Field(default=50, ge=1, le=1000)
    block_market_open: bool = Field(default=True)

    # Optimization settings
    max_workers: int = Field(default=4, ge=1, le=8)

    # Result filters (optional)
    max_drawdown_limit: Optional[float] = None  # Only keep results with max DD below this %
    min_win_rate: Optional[float] = None        # Only keep results with win rate above this %

class OptimizationResultItem(BaseModel):
    """Single optimization result."""
    rank: int
    parameters: Dict[str, Any]
    sessions: List[str]
    total_return: float
    win_rate: float
    trade_count: int
    max_drawdown: float

class OptimizationResponse(BaseModel):
    """Response from optimization."""
    id: str
    strategy_name: str
    total_combinations: int
    completed: int
    top_results: List[OptimizationResultItem]
    errors: int = 0


def generate_session_combinations(sessions: List[str]) -> List[List[str]]:
    """Generate all non-empty subsets of sessions."""
    combos = []
    for r in range(1, len(sessions) + 1):
        for combo in itertools.combinations(sessions, r):
            combos.append(list(combo))
    return combos


def generate_param_values(param: ParameterRangeInput) -> List[Any]:
    """Generate values from a parameter range."""
    if param.param_type == "bool":
        if param.min_value == param.max_value:
            return [bool(param.min_value)]
        return [True, False]
    elif param.param_type == "str_options":
        # String options are stored in 'str_values' field
        if hasattr(param, 'str_values') and param.str_values:
            return param.str_values
        # Fallback: single value (min_value treated as index or direct value)
        return [param.min_value] if param.min_value == param.max_value else []
    elif param.param_type == "int":
        return list(range(int(param.min_value), int(param.max_value) + 1, int(param.step)))
    else:
        values = []
        current = param.min_value
        while current <= param.max_value + 1e-9:
            values.append(round(current, 6))
            current += param.step
        return values


def filter_trades_by_sessions(trades: List[Dict], sessions: List[str]) -> List[Dict]:
    """Filter trades to only include those in specified sessions."""
    return [t for t in trades if t.get("session") in sessions]


def calculate_metrics_from_trades(trades: List[Dict], initial_equity: float) -> Dict[str, float]:
    """Calculate metrics from a list of trades."""
    if not trades:
        return {
            "total_return": 0.0,
            "win_rate": 0.0,
            "trade_count": 0,
            "max_drawdown": 0.0
        }

    total_pnl = sum(t["pnl"] for t in trades)
    winning = [t for t in trades if t["pnl"] > 0]
    win_rate = (len(winning) / len(trades) * 100) if trades else 0.0

    # Calculate max drawdown from cumulative PnL
    cumulative = 0.0
    peak = 0.0
    max_dd = 0.0

    for t in trades:
        cumulative += t["pnl"]
        if cumulative > peak:
            peak = cumulative
        
        # Drawdown is relative to Peak Equity (Initial + Peak PnL)
        peak_equity = initial_equity + peak
        if peak_equity > 0:
            dd = (peak - cumulative) / peak_equity
        else:
             dd = 0.0 # Or 1.0 (100%) if equity is 0? Let's say 0 to avoid spikes if logic fails.
             
        if dd > max_dd:
            max_dd = dd

    return {
        "total_return": (total_pnl / initial_equity * 100) if initial_equity > 0 else 0.0,
        "win_rate": win_rate,
        "trade_count": len(trades),
        "max_drawdown": max_dd * 100
    }


# Optimization history storage
OPTIMIZATION_HISTORY_FILE = Path.home() / ".nebular-apollo" / "optimization_history.json"


def save_optimization_result(result: Dict) -> None:
    """Save optimization result to history."""
    OPTIMIZATION_HISTORY_FILE.parent.mkdir(exist_ok=True)

    # Ensure is_favorite is set
    if "is_favorite" not in result:
        result["is_favorite"] = False

    history = []
    if OPTIMIZATION_HISTORY_FILE.exists():
        try:
            with open(OPTIMIZATION_HISTORY_FILE, 'r') as f:
                history = json.load(f)
        except:
            pass

    history.append(result)

    # Keep only last 100
    if len(history) > 100:
        history = history[-100:]

    with open(OPTIMIZATION_HISTORY_FILE, 'w') as f:
        json.dump(history, f, indent=2)


def load_optimization_history() -> List[Dict]:
    """Load optimization history."""
    if not OPTIMIZATION_HISTORY_FILE.exists():
        return []

    try:
        with open(OPTIMIZATION_HISTORY_FILE, 'r') as f:
            return json.load(f)
    except:
        return []


def toggle_optimization_favorite(run_id: str) -> Optional[bool]:
    """Toggle favorite status. Returns new state or None if not found."""
    if not OPTIMIZATION_HISTORY_FILE.exists():
        return None

    try:
        with open(OPTIMIZATION_HISTORY_FILE, 'r') as f:
            history = json.load(f)
        
        found = False
        new_state = False
        
        for h in history:
            if h["id"] == run_id:
                h["is_favorite"] = not h.get("is_favorite", False)
                new_state = h["is_favorite"]
                found = True
                break
        
        if not found:
            return None
            
        with open(OPTIMIZATION_HISTORY_FILE, 'w') as f:
            json.dump(history, f, indent=2)
            
        return new_state
    except Exception as e:
        logger.error(f"Failed to toggle favorite for {run_id}: {e}")
        return None


def delete_optimization_runs(run_ids: List[str]) -> int:
    """Delete multiple optimization runs from history. Returns count of deleted items."""
    if not OPTIMIZATION_HISTORY_FILE.exists():
        return 0

    try:
        with open(OPTIMIZATION_HISTORY_FILE, 'r') as f:
            history = json.load(f)
        
        original_len = len(history)
        history = [h for h in history if h["id"] not in run_ids]
        
        if len(history) == original_len:
            return 0
            
        with open(OPTIMIZATION_HISTORY_FILE, 'w') as f:
            json.dump(history, f, indent=2)
            
        return original_len - len(history)
    except Exception as e:
        logger.error(f"Failed to delete runs: {e}")
        return 0


@router.post("/optimize", response_model=OptimizationResponse)
def run_optimization(req: OptimizationRequest):
    """
    Run parameter optimization for a strategy.

    Tests all combinations of parameters × sessions and returns the top 20 results.
    """
    load_strategies()

    if req.strategy_name not in STRATEGIES:
        raise HTTPException(status_code=404, detail="Strategy not found")

    StrategyClass = STRATEGIES[req.strategy_name]
    strategy_instance = StrategyClass()

    # Determine parameter ranges
    if req.parameters:
        # Use custom ranges from request
        param_ranges = {}
        for p in req.parameters:
            param_ranges[p.name] = generate_param_values(p)
    else:
        # Use strategy's default param_ranges
        param_ranges = getattr(strategy_instance, 'param_ranges', {})
        if not param_ranges:
            raise HTTPException(
                status_code=400,
                detail=f"Strategy {req.strategy_name} has no param_ranges defined and no custom parameters provided"
            )

    # Generate all parameter combinations
    param_keys = list(param_ranges.keys())
    param_values = list(param_ranges.values())
    param_combinations = list(itertools.product(*param_values))

    # Generate session combinations
    session_combinations = generate_session_combinations(req.sessions)

    total_combinations = len(param_combinations) * len(session_combinations)
    logger.info(f"Starting optimization: {len(param_combinations)} param combos × {len(session_combinations)} session combos = {total_combinations} total")

    # Warn if too many combinations
    if total_combinations > 5000:
        raise HTTPException(
            status_code=400,
            detail=f"Too many combinations ({total_combinations}). Maximum is 5000. Reduce parameter ranges or sessions."
        )

    # Fetch data ONCE (it will be cached)
    
    # Parse Date Range if provided
    if req.start_date and req.end_date:
        try:
            original_start_date = pd.to_datetime(req.start_date).replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = pd.to_datetime(req.end_date).replace(hour=23, minute=59, second=59, microsecond=999999)
            req.days = (end_date - original_start_date).days
        except:
             end_date = datetime.now()
             original_start_date = end_date - timedelta(days=req.days)
    else:
        end_date = datetime.now()
        original_start_date = end_date - timedelta(days=req.days)

    # Warmup
    warmup_bars = 1000
    map_min = {"1m": 1, "2m": 2, "3m": 3, "5m": 5, "7m": 7, "15m": 15, "30m": 30, "60m": 60, "1h": 60, "4h": 240, "1d": 1440}
    minutes_per_bar = map_min.get(req.interval, 15)
    total_minutes = warmup_bars * minutes_per_bar * 1.5
    warmup_delta = timedelta(minutes=total_minutes)
    start_date = original_start_date - warmup_delta
    logger.info(f"Optimization Data Fetch: Start={start_date}, End={end_date}, Live={req.topstep_live_mode}")

    # Fetch data
    try:
        data = pd.DataFrame()
        if req.source == "Topstep":
            if not req.contract_id:
                raise HTTPException(status_code=400, detail="Contract ID required for Topstep")
            
            # Using Live Mode in cache key
            current_params = (req.contract_id, req.interval, req.days, req.topstep_live_mode, str(original_start_date.date()), str(end_date.date()))
            
            if TOPSTEP_CACHE["params"] == current_params and TOPSTEP_CACHE["data"] is not None:
                data = TOPSTEP_CACHE["data"].copy()
                if TOPSTEP_CACHE["original_start_date"]:
                    original_start_date = TOPSTEP_CACHE["original_start_date"]
            else:
                # Force live=False for Historical
                data = topstep.fetch_historical_data(req.contract_id, start_date, end_date, req.interval, live=False)
                TOPSTEP_CACHE["params"] = current_params
                TOPSTEP_CACHE["data"] = data.copy()
                TOPSTEP_CACHE["original_start_date"] = original_start_date
                
             # --- Fetch Contract Details (Copy of logic from run_backtest) ---
            if not req.topstep_live_mode:
                 try:
                     details = topstep.get_contract_details(req.contract_id)
                     if details:
                         # Store specifically for this optimization run context?
                         # Optimization logic below re-fetches specs. We need to pass it down.
                         # Or just verify we have tick sizes.
                         # We'll update current local variables to guide the loop below.
                         fetched_tick_size = details.get("tickSize")
                         fetched_tick_value = details.get("tickValue")
                         if fetched_tick_size and fetched_tick_value:
                             # We'll use this in the "Get contract specs" section
                             pass
                 except Exception:
                     pass
        else:
            data = yf.download(req.ticker, start=start_date, end=end_date, interval=req.interval, progress=False, auto_adjust=True)
            if isinstance(data.columns, pd.MultiIndex):
                data.columns = data.columns.droplevel(1)

        if data.empty:
            raise HTTPException(status_code=400, detail=f"No data found")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Data fetch error: {str(e)}")

    # Get contract specs
    tick_size = 0.25
    tick_value = 5.0
    point_value = 1.0
    fee_per_trade = 0.0

    if req.source == "Topstep" and req.contract_id:
        try:
            contracts = topstep.fetch_available_contracts()
            contract = next((c for c in contracts if str(c['id']) == str(req.contract_id)), None)
            if contract:
                tick_size = float(contract.get('tickSize', 0.25))
                tick_value = float(contract.get('tickValue', 5.0))
                contract_name = contract.get('name', '').upper()
                if tick_size > 0:
                    point_value = tick_value / tick_size

                sorted_keys = sorted(FEES_MAP.keys(), key=len, reverse=True)
                for k in sorted_keys:
                    if k in contract_name:
                        fee_per_trade = FEES_MAP[k]
                        break
            
            # CHECK LEGACY MANUAL FETCH (Override logic)
            if not req.topstep_live_mode:
                 details = topstep.get_contract_details(req.contract_id)
                 if details:
                     tick_size = float(details.get("tickSize", 0.25))
                     tick_value = float(details.get("tickValue", 5.0))
                     if tick_size > 0:
                         point_value = tick_value / tick_size

            # Override with hardcoded specs
            sorted_spec_keys = sorted(CONTRACT_SPECS.keys(), key=len, reverse=True)
            for k in sorted_spec_keys:
                if contract and k in contract.get('name', '').upper():
                    spec = CONTRACT_SPECS[k]
                    tick_size = spec['tick_size']
                    tick_value = spec['tick_value']
                    if tick_size > 0:
                        point_value = tick_value / tick_size
                    break
        except:
            pass

    # Run all backtests sequentially (parallelization would require process-safe data sharing)
    all_results = []
    errors = 0
    completed = 0

    for param_combo in param_combinations:
        params = dict(zip(param_keys, param_combo))
        params['tick_size'] = tick_size

        # Merge with strategy defaults
        full_params = strategy_instance.default_params.copy()
        full_params.update(params)

        try:
            # Run strategy
            signals = strategy_instance.generate_signals(data.copy(), full_params)

            exec_price = None
            sl_dist_series = None
            exit_ratios = None

            if len(signals) == 7:
                long_entries, long_exits, short_entries, short_exits, exec_price, sl_dist_series, exit_ratios = signals
            elif len(signals) == 6:
                long_entries, long_exits, short_entries, short_exits, exec_price, sl_dist_series = signals
            elif len(signals) == 5:
                long_entries, long_exits, short_entries, short_exits, exec_price = signals
            elif len(signals) == 4:
                long_entries, long_exits, short_entries, short_exits = signals
            else:
                long_entries, short_entries = signals
                long_exits = None
                short_exits = None

            # Apply warmup slicing
            ts_start = pd.Timestamp(original_start_date)
            if data.index.tz is not None:
                if ts_start.tzinfo is None:
                    ts_start = ts_start.tz_localize(data.index.tz)
                else:
                    ts_start = ts_start.tz_convert(data.index.tz)

            mask = data.index >= ts_start
            sliced_data = data.loc[mask].copy()

            long_entries = long_entries.loc[mask]
            short_entries = short_entries.loc[mask]
            if long_exits is not None: long_exits = long_exits.loc[mask]
            if short_exits is not None: short_exits = short_exits.loc[mask]
            if exec_price is not None: exec_price = exec_price.loc[mask]
            if sl_dist_series is not None: sl_dist_series = sl_dist_series.loc[mask]
            if exit_ratios is not None: exit_ratios = exit_ratios.loc[mask]

            # Apply Topstep time filter
            if req.source == "Topstep":
                try:
                    temp_index = sliced_data.index
                    if temp_index.tz is None:
                        temp_index = temp_index.tz_localize('UTC')
                    else:
                        temp_index = temp_index.tz_convert('UTC')
                    temp_index_paris = temp_index.tz_convert('Europe/Paris')
                    time_mask = (temp_index_paris.hour >= 22)
                    long_entries = long_entries & (~time_mask)
                    short_entries = short_entries & (~time_mask)
                except:
                    time_mask = sliced_data.index.hour >= 21
                    long_entries = long_entries & (~time_mask)
                    short_entries = short_entries & (~time_mask)

            # Apply market open filter (block first 5 min of each session)
            if req.block_market_open:
                try:
                    temp_index = sliced_data.index
                    if temp_index.tz is None:
                        temp_index = temp_index.tz_localize('UTC')
                    else:
                        temp_index = temp_index.tz_convert('UTC')
                    temp_index_paris = temp_index.tz_convert('Europe/Paris')
                    hours = temp_index_paris.hour
                    minutes = temp_index_paris.minute
                    time_minutes = hours * 60 + minutes

                    # Block: 0h00-0h05, 9h00-9h05, 15h30-15h35
                    market_open_mask = (
                        ((time_minutes >= 0) & (time_minutes < 5)) |
                        ((time_minutes >= 540) & (time_minutes < 545)) |
                        ((time_minutes >= 930) & (time_minutes < 935))
                    )
                    long_entries = long_entries & (~market_open_mask)
                    short_entries = short_entries & (~market_open_mask)
                except:
                    pass

            # Position sizing
            risk_amount = req.initial_equity * req.risk_per_trade
            if sl_dist_series is not None:
                safe_sl = sl_dist_series.replace(0, tick_size).abs()
                sl_ticks = safe_sl / tick_size
                raw_sizes = risk_amount / (sl_ticks * tick_value)
                entry_sizes = np.maximum(1.0, np.floor(raw_sizes)).fillna(1.0)
                entry_sizes = np.minimum(entry_sizes, req.max_contracts)
            else:
                entry_sizes = pd.Series(1.0, index=sliced_data.index)

            size_series = entry_sizes.copy()

            # FIFO for longs
            current_long_qty = 0.0
            idx_long_entry = np.where(long_entries)[0]
            idx_long_exit = np.where(long_exits)[0] if long_exits is not None else []
            combined_long_indices = sorted(np.unique(np.concatenate([idx_long_entry, idx_long_exit])))

            for i in combined_long_indices:
                is_entry = long_entries.iloc[i]
                is_exit = long_exits.iloc[i] if long_exits is not None else False
                if is_entry:
                    qty = entry_sizes.iloc[i]
                    current_long_qty += qty
                    size_series.iloc[i] = qty
                if is_exit:
                    ratio = exit_ratios.iloc[i] if exit_ratios is not None else 1.0
                    if current_long_qty > 0:
                        if ratio >= 0.99:
                            exit_amt = current_long_qty
                        else:
                            exit_amt = max(1.0, round(current_long_qty * ratio))
                        size_series.iloc[i] = min(exit_amt, current_long_qty)
                        current_long_qty -= size_series.iloc[i]

            # FIFO for shorts
            current_short_qty = 0.0
            idx_short_entry = np.where(short_entries)[0] if short_entries is not None else []
            idx_short_exit = np.where(short_exits)[0] if short_exits is not None else []
            combined_short_indices = sorted(np.unique(np.concatenate([idx_short_entry, idx_short_exit])))

            for i in combined_short_indices:
                is_entry = short_entries.iloc[i] if short_entries is not None else False
                is_exit = short_exits.iloc[i] if short_exits is not None else False
                if is_entry:
                    qty = entry_sizes.iloc[i]
                    current_short_qty += qty
                    size_series.iloc[i] = qty
                if is_exit:
                    ratio = exit_ratios.iloc[i] if exit_ratios is not None else 1.0
                    if current_short_qty > 0:
                        if ratio >= 0.99:
                            exit_amt = current_short_qty
                        else:
                            exit_amt = max(1.0, round(current_short_qty * ratio))
                        size_series.iloc[i] = min(exit_amt, current_short_qty)
                        current_short_qty -= size_series.iloc[i]

            # Run VBT portfolio
            price_to_use = exec_price if exec_price is not None else sliced_data['Close']
            sim_cash = 1_000_000_000.0

            pf = vbt.Portfolio.from_signals(
                close=price_to_use,
                entries=long_entries,
                exits=long_exits,
                short_entries=short_entries,
                short_exits=short_exits,
                init_cash=sim_cash,
                freq=req.interval,
                size=size_series,
                size_type='Amount',
                accumulate=True,
                fees=0.0,
                slippage=0.0,
                sl_stop=None
            )

            # Extract trades with session info
            trades_df = pf.trades.records_readable
            trades_list = []

            exec_price_lookup = {}
            if exec_price is not None:
                for idx, val in exec_price.items():
                    exec_price_lookup[str(idx)] = float(val)
                    if hasattr(idx, 'strftime'):
                        exec_price_lookup[idx.strftime('%Y-%m-%d %H:%M:%S')] = float(val)

            aggregated_trades = {}
            for _, row in trades_df.iterrows():
                entry_time_str = str(row['Entry Timestamp'])
                exit_time_str = str(row['Exit Timestamp'])

                exit_timestamp = row['Exit Timestamp']
                entry_timestamp = row['Entry Timestamp']

                if hasattr(exit_timestamp, 'strftime'):
                    exit_time_normalized = exit_timestamp.strftime('%Y-%m-%d %H:%M:%S')
                else:
                    exit_time_normalized = str(exit_timestamp)[:19]

                if hasattr(entry_timestamp, 'strftime'):
                    entry_time_normalized = entry_timestamp.strftime('%Y-%m-%d %H:%M:%S')
                else:
                    entry_time_normalized = str(entry_timestamp)[:19]

                size = float(row['Size'])
                direction = row['Direction']

                entry_price_trade = exec_price_lookup.get(entry_time_str) or exec_price_lookup.get(entry_time_normalized) or float(row['Avg Entry Price'])
                exit_price_trade = exec_price_lookup.get(exit_time_str) or exec_price_lookup.get(exit_time_normalized) or float(row['Avg Exit Price'])

                def round_to_tick(price, ts):
                    if ts > 0:
                        return round(price / ts) * ts
                    return price

                entry_price_trade = round_to_tick(entry_price_trade, tick_size)
                exit_price_trade = round_to_tick(exit_price_trade, tick_size)

                if direction == 'Long':
                    raw_pnl_points = exit_price_trade - entry_price_trade
                else:
                    raw_pnl_points = entry_price_trade - exit_price_trade

                gross_pnl = raw_pnl_points * size * point_value
                total_fee = fee_per_trade * size
                real_pnl = gross_pnl - total_fee

                if entry_time_str not in aggregated_trades:
                    aggregated_trades[entry_time_str] = {
                        "entry_time": entry_time_str,
                        "exit_time": exit_time_str,
                        "side": direction,
                        "entry_price": entry_price_trade,
                        "net_pnl": 0.0,
                        "gross_pnl": 0.0,
                        "fees": 0.0,
                        "total_size": 0.0,
                        "exit_p_accum": 0.0,
                        "exit_size_accum": 0.0,
                    }

                group = aggregated_trades[entry_time_str]
                group["net_pnl"] += real_pnl
                group["gross_pnl"] += gross_pnl
                group["fees"] += total_fee
                group["total_size"] += size
                group["exit_p_accum"] += (exit_price_trade * size)
                group["exit_size_accum"] += size

                if row['Exit Timestamp'] > pd.to_datetime(group["exit_time"]):
                    group["exit_time"] = exit_time_str

            # Convert to list with session info
            for k in sorted(aggregated_trades.keys()):
                t = aggregated_trades[k]
                avg_exit = t["exit_p_accum"] / t["exit_size_accum"] if t["exit_size_accum"] > 0 else 0.0
                session = get_session(t["entry_time"])

                trades_list.append({
                    "entry_time": t["entry_time"],
                    "exit_time": t["exit_time"],
                    "side": t["side"],
                    "entry_price": t["entry_price"],
                    "exit_price": avg_exit,
                    "pnl": t["net_pnl"],
                    "gross_pnl": t["gross_pnl"],
                    "fees": t["fees"],
                    "size": t["total_size"],
                    "session": session
                })

            # Now test each session combination
            for session_combo in session_combinations:
                filtered_trades = filter_trades_by_sessions(trades_list, session_combo)
                metrics = calculate_metrics_from_trades(filtered_trades, req.initial_equity)

                all_results.append({
                    "params": params,
                    "sessions": session_combo,
                    "total_return": metrics["total_return"],
                    "win_rate": metrics["win_rate"],
                    "trade_count": metrics["trade_count"],
                    "max_drawdown": metrics["max_drawdown"],
                })

                completed += 1

        except Exception as e:
            logger.error(f"Error with params {params}: {e}")
            errors += len(session_combinations)
            completed += len(session_combinations)

    # Apply optional result filters
    if req.max_drawdown_limit is not None:
        all_results = [r for r in all_results if r["max_drawdown"] <= req.max_drawdown_limit]
    if req.min_win_rate is not None:
        all_results = [r for r in all_results if r["win_rate"] >= req.min_win_rate]

    # Sort by total_return descending and get top 20
    all_results.sort(key=lambda x: x["total_return"], reverse=True)
    top_20 = all_results[:20]

    # Format response
    top_results = []
    for rank, res in enumerate(top_20, 1):
        top_results.append(OptimizationResultItem(
            rank=rank,
            parameters=res["params"],
            sessions=res["sessions"],
            total_return=round(res["total_return"], 2),
            win_rate=round(res["win_rate"], 1),
            trade_count=res["trade_count"],
            max_drawdown=round(res["max_drawdown"], 2)
        ))

    # Generate ID and save
    run_id = str(uuid4())[:8]

    # Save to history
    history_entry = {
        "id": run_id,
        "timestamp": datetime.now().isoformat(),
        "strategy_name": req.strategy_name,
        "contract_id": req.contract_id,
        "ticker": req.ticker,
        "source": req.source,
        "interval": req.interval,
        "days": req.days,
        "start_date": req.start_date,
        "end_date": req.end_date,
        "topstep_live_mode": req.topstep_live_mode,
        "initial_equity": req.initial_equity,
        "risk_per_trade": req.risk_per_trade,
        "sessions_tested": req.sessions,
        "parameters": [p.dict() for p in req.parameters],
        "total_combinations": total_combinations,
        "top_results": [r.model_dump() for r in top_results],
        "max_drawdown_limit": req.max_drawdown_limit,
        "min_win_rate": req.min_win_rate,
    }
    save_optimization_result(history_entry)

    return OptimizationResponse(
        id=run_id,
        strategy_name=req.strategy_name,
        total_combinations=total_combinations,
        completed=completed,
        top_results=top_results,
        errors=errors
    )


@router.get("/optimization-history")
def get_optimization_history():
    """Get list of past optimization runs."""
    history = load_optimization_history()
    # Return summary only (not full top_results to keep response small)
    return [{
        "id": h["id"],
        "timestamp": h["timestamp"],
        "strategy_name": h["strategy_name"],
        "contract_id": h.get("contract_id"),
        "ticker": h.get("ticker", ""),
        "source": h.get("source", "Topstep"),
        "interval": h.get("interval", "15m"),
        "days": h.get("days", 14),
        "total_combinations": h.get("total_combinations", 0),
        "best_return": h["top_results"][0]["total_return"] if h.get("top_results") else 0,
        "is_favorite": h.get("is_favorite", False)
    } for h in history]


@router.get("/optimization-history/{run_id}")
def get_optimization_run(run_id: str):
    """Get details of a specific optimization run."""
    history = load_optimization_history()
    for h in history:
        if h["id"] == run_id:
            return h
    raise HTTPException(status_code=404, detail="Optimization run not found")


def delete_optimization_run(run_id: str) -> bool:
    """Delete an optimization run from history."""
    if not OPTIMIZATION_HISTORY_FILE.exists():
        return False

    try:
        with open(OPTIMIZATION_HISTORY_FILE, 'r') as f:
            history = json.load(f)
        
        original_len = len(history)
        history = [h for h in history if h["id"] != run_id]
        
        if len(history) == original_len:
            return False
            
        with open(OPTIMIZATION_HISTORY_FILE, 'w') as f:
            json.dump(history, f, indent=2)
            
        return True
    except Exception as e:
        logger.error(f"Failed to delete run {run_id}: {e}")
        return False


class BulkDeleteRequest(BaseModel):
    run_ids: List[str]

@router.delete("/optimization-history/{run_id}")
def delete_optimization_history_item(run_id: str):
    """Delete a specific optimization run."""
    count = delete_optimization_runs([run_id])
    if count == 0:
        raise HTTPException(status_code=404, detail="Optimization run not found or could not be deleted")
    return {"status": "success", "message": f"Run {run_id} deleted"}

@router.post("/optimization-history/bulk-delete")
def bulk_delete_optimization_history_items(req: BulkDeleteRequest):
    """Delete multiple optimization runs."""
    count = delete_optimization_runs(req.run_ids)
    return {"status": "success", "message": f"Deleted {count} runs", "deleted_count": count}

@router.post("/optimization-history/{run_id}/favorite")
def toggle_optimization_history_favorite(run_id: str):
    """Toggle favorite status of an optimization run."""
    new_state = toggle_optimization_favorite(run_id)
    if new_state is None:
        raise HTTPException(status_code=404, detail="Optimization run not found")
    return {"status": "success", "is_favorite": new_state}


@router.get("/strategy-param-ranges/{strategy_name}")
def get_strategy_param_ranges(strategy_name: str):
    """Get the default parameter ranges for a strategy."""
    load_strategies()

    if strategy_name not in STRATEGIES:
        raise HTTPException(status_code=404, detail="Strategy not found")

    StrategyClass = STRATEGIES[strategy_name]
    strategy_instance = StrategyClass()

    param_ranges = getattr(strategy_instance, 'param_ranges', {})
    default_params = getattr(strategy_instance, 'default_params', {})

    # Convert to structured format
    ranges_info = []
    for name, values in param_ranges.items():
        if isinstance(values, (list, tuple)):
            if all(isinstance(v, bool) for v in values):
                param_type = "bool"
            elif all(isinstance(v, str) for v in values):
                param_type = "str_options"
            elif all(isinstance(v, int) for v in values):
                param_type = "int"
            else:
                param_type = "float"

            ranges_info.append({
                "name": name,
                "values": values,
                "default": default_params.get(name),
                "param_type": param_type,
                "count": len(values)
            })

    return {
        "strategy_name": strategy_name,
        "param_ranges": ranges_info,
        "total_combinations": int(np.prod([len(r["values"]) for r in ranges_info])) if ranges_info else 0
    }
