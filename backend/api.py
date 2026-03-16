import logging
import sys
import os
import inspect
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional

import pandas as pd
import numpy as np
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, field_validator

try:
    import vectorbt as vbt
except ModuleNotFoundError:  # pragma: no cover - optional for simulator-only test runs
    vbt = None

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

# --- Strategy warmup bars ---
# Bars required for FULL indicator convergence (not just first value).
# Formula: max(chain_depth) + 4 × max(EMA/rolling period) + safety margin.
# EMA(n) converges to 99% accuracy after ~4n bars from first valid value.
STRATEGY_WARMUP_BARS = {
    "EMA9Retest": 80,       # EMA(9): 9+36=45, + margin
    "RobReversal": 60,      # Short lookbacks
    "DeltaDiv": 200,        # MFI(35)+cloud(35)+EMA(30)=100, convergence ~200
    "UTBotSTC": 220,        # STC uses EMA(50)+convergence
    "UTBotOCC": 200,        # EMA(200/50) based
    "UTBotHeikin": 500,     # EMA(200): 200+4*200=1000 ideal, 500 pragmatic
    "BullesBollinger": 100, # BB(20)+convergence
    "Brochettes": 60,       # Short lookbacks
    "EMABreakOsc": 250,     # EMA(30)→100 + MFI(35)+cloud(35)→112 + margin
    "VwapEmaStrategy": 80,  # VWAP resets daily, EMA short
    "MACrossover": 500,     # MA(200): needs ~400+ bars convergence
    "RSIReversal": 100,     # RSI(14)+convergence
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

    try:
        signals = strategy_instance.generate_signals(data, params)
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
        cooldown_bars=int(sliced_signals.get("cooldown_bars", params.get("cooldown_bars", 0))),
        tp1_execution_mode=str(simulator_settings.get("tp1_execution_mode", "touch")),
        tp1_partial_pct=float(simulator_settings.get("tp1_partial_pct", 0.25)),
        tp2_partial_pct=float(simulator_settings.get("tp2_partial_pct", 0.25)),
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

    if getattr(strategy_instance, "use_simulator", False):
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

    if vbt is None:
        raise HTTPException(status_code=500, detail="vectorbt is required for legacy backtests in this environment")
    
    # 3. Simulate (VectorBT)
    try:
        signals = strategy_instance.generate_signals(data, params)
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
            
        # --- WARMUP SLICING ---
        # Now that indicators are calculated on full history, we slice everything to the Requested Period.
        if warmup_bars > 0:
            # Mask: Keep only data >= original_start_date
            # Ensure timezone awareness match
            
            # Convert original_start_date to match index tz if needed
            ts_start = pd.Timestamp(original_start_date)
            if data.index.tz is not None:
                if ts_start.tzinfo is None:
                     # Assume input was local/naive, but we used it to fetch. 
                     # Ideally utilize the same timezone as data.
                     ts_start = ts_start.tz_localize(data.index.tz)
                else:
                     ts_start = ts_start.tz_convert(data.index.tz)
            
            mask = data.index >= ts_start
            
            # Slice Data
            data = data.loc[mask]
            
            # Slice Signals
            long_entries = long_entries.loc[mask]
            short_entries = short_entries.loc[mask]
            
            if long_exits is not None: long_exits = long_exits.loc[mask]
            if short_exits is not None: short_exits = short_exits.loc[mask]
            if exec_price is not None: exec_price = exec_price.loc[mask]
            if sl_dist_series is not None: sl_dist_series = sl_dist_series.loc[mask]
            if exit_ratios is not None: exit_ratios = exit_ratios.loc[mask]
            
            if data.empty:
                 raise HTTPException(status_code=400, detail="Data empty after warmup slicing. Fetch more history?")

        # --- Time Filter (22:00 - 00:00 Paris Time) ---
        if True:  # Always apply - data is from futures markets
            try:
                temp_index = data.index
                if temp_index.tz is None:
                    temp_index = temp_index.tz_localize('UTC')
                else:
                    temp_index = temp_index.tz_convert('UTC')

                temp_index_paris = temp_index.tz_convert('Europe/Paris')
                time_mask = (temp_index_paris.hour >= 22)

                if long_entries is not None:
                    long_entries = long_entries & (~time_mask)

                if short_entries is not None:
                    short_entries = short_entries & (~time_mask)
            except Exception as e:
                logger.warning(f"Timezone conversion failed for filter: {e}")
                time_mask = data.index.hour >= 21
                if long_entries is not None:
                    long_entries = long_entries & (~time_mask)
                if short_entries is not None:
                    short_entries = short_entries & (~time_mask)

        # --- Market Open Filter (block first 5 min of each session) ---
        # Sessions: Asia (0h00-0h05), UK (9h00-9h05), US (15h30-15h35)
        if False and req.block_market_open:
            try:
                temp_index = data.index
                if temp_index.tz is None:
                    temp_index = temp_index.tz_localize('UTC')
                else:
                    temp_index = temp_index.tz_convert('UTC')

                temp_index_paris = temp_index.tz_convert('Europe/Paris')
                hours = temp_index_paris.hour
                minutes = temp_index_paris.minute
                time_minutes = hours * 60 + minutes

                # Block: 0h00-0h05, 9h00-9h05, 15h30-15h35 (in minutes: 0-5, 540-545, 930-935)
                market_open_mask = (
                    ((time_minutes >= 0) & (time_minutes < 5)) |       # Asia: 0h00-0h05
                    ((time_minutes >= 540) & (time_minutes < 545)) |   # UK: 9h00-9h05
                    ((time_minutes >= 930) & (time_minutes < 935))     # US: 15h30-15h35
                )

                if long_entries is not None:
                    long_entries = long_entries & (~market_open_mask)
                if short_entries is not None:
                    short_entries = short_entries & (~market_open_mask)

                logger.info(f"Market open filter applied: blocked {market_open_mask.sum()} bars")
            except Exception as e:
                logger.warning(f"Market open filter failed: {e}")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Strategy execution error: {str(e)}")

    # 4. Position Sizing & Contract Specs from local lookup
    size_series = pd.Series(0.0, index=data.index)
    point_value = 1.0
    tick_size = 0.25
    tick_value = 12.5
    fee_per_trade = 0.0

    # Use CONTRACT_SPECS for the symbol
    if req.symbol in CONTRACT_SPECS:
        spec = CONTRACT_SPECS[req.symbol]
        tick_size = spec['tick_size']
        tick_value = spec['tick_value']
        if tick_size > 0:
            point_value = tick_value / tick_size

    # Fee from FEES_MAP
    if req.symbol in FEES_MAP:
        fee_per_trade = FEES_MAP[req.symbol]

    logger.info(f"Contract specs for {req.symbol}: tick_size={tick_size}, tick_value={tick_value}, point_value={point_value}, fee={fee_per_trade}")
            
    # Calculate Base Sizing (Entries)
    risk_amount = req.initial_equity * req.risk_per_trade
    
    # If strategy provided specific SL distances, use them
    if sl_dist_series is not None:
        safe_sl = sl_dist_series.replace(0, tick_size)

        # Ensure positive distance (Reciprocity: Short dist should be positive)
        safe_sl = safe_sl.abs()

        sl_ticks = safe_sl / tick_size
        raw_sizes = risk_amount / (sl_ticks * tick_value)

        # Round down to nearest int, min 1, max max_contracts
        entry_sizes = np.maximum(1.0, np.floor(raw_sizes)).fillna(1.0)
        entry_sizes = np.minimum(entry_sizes, req.max_contracts)
    else:
        # Fallback to strategy.get_stop_loss if available
        # We need to iterate entries to get dynamic SL
        entry_sizes = pd.Series(1.0, index=data.index)
        
        # Check if strategy overrides get_stop_loss (heuristic: if it's not base method? 
        # Or just try calling it. Base returns None.)
        
        # We process Long Entries
        long_indices = np.where(long_entries)[0]
        for idx in long_indices:
             try:
                 sl_price = strategy_instance.get_stop_loss(data, idx, params)
                 if sl_price is not None:
                     entry_price = data['Close'].iloc[idx]
                     risk_per_share = abs(entry_price - sl_price)
                     if risk_per_share > 0:
                         # Size = RiskAmount / (RiskPerShare * PointValue * ? No, RiskAmount / (RiskPerContract))
                         # RiskPerContract = (RiskTicks) * TickValue
                         # RiskTicks = RiskPrice / TickSize
                         # Same as: RiskAmount / ( (RiskPrice/TickSize) * TickValue )
                         
                         risk_ticks = risk_per_share / tick_size
                         calc_size = risk_amount / (risk_ticks * tick_value)
                         entry_sizes.iloc[idx] = min(req.max_contracts, max(1.0, float(int(calc_size))))
             except Exception as e:
                 # logger.warning(f"Error getting SL: {e}")
                 pass

        # For Shorts, technically similar, but let's stick to Long logic for MVP or Duplicate
        short_indices = np.where(short_entries)[0]
        for idx in short_indices:
             try:
                 sl_price = strategy_instance.get_stop_loss(data, idx, params)
                 if sl_price is not None:
                     entry_price = data['Close'].iloc[idx]
                     risk_per_share = abs(entry_price - sl_price)
                     if risk_per_share > 0:
                         risk_ticks = risk_per_share / tick_size
                         calc_size = risk_amount / (risk_ticks * tick_value)
                         entry_sizes.iloc[idx] = min(req.max_contracts, max(1.0, float(int(calc_size))))
             except:
                 pass

    # --- Sizing Adjustment Loop for Partial Exits ---
    # We iterate chronologically to determine Held Quantity and construct Size Series for Exits
    # VectorBT expects 'size' at index to be the Order Amount.
    # Entries: Size provided. Exits: Size provided.
    # We must match Exits to Entries to know held quantity.

    # Pre-fill size series with entry sizes (only relevant at entry indices)
    size_series = entry_sizes.copy()

    # ===== LONG POSITIONS =====
    current_long_qty = 0.0

    idx_long_entry = np.where(long_entries)[0]
    idx_long_exit = np.where(long_exits)[0] if long_exits is not None else []

    combined_long_indices = sorted(np.unique(np.concatenate([idx_long_entry, idx_long_exit])))

    # FIFO Simulation for Long positions
    for i in combined_long_indices:
        is_entry = long_entries.iloc[i]
        is_exit = long_exits.iloc[i] if long_exits is not None else False

        if is_entry:
            qty = entry_sizes.iloc[i]
            current_long_qty += qty
            size_series.iloc[i] = qty

        if is_exit:
            ratio = 1.0
            if exit_ratios is not None:
                ratio = exit_ratios.iloc[i]

            if current_long_qty > 0:
                if ratio >= 0.99:
                    exit_amt = current_long_qty
                else:
                    exit_amt = current_long_qty * ratio
                    exit_amt = max(1.0, round(exit_amt))
                    if exit_amt > current_long_qty:
                        exit_amt = current_long_qty

                size_series.iloc[i] = exit_amt
                current_long_qty -= exit_amt
            else:
                size_series.iloc[i] = 0.0

    # ===== SHORT POSITIONS =====
    current_short_qty = 0.0

    idx_short_entry = np.where(short_entries)[0] if short_entries is not None else []
    idx_short_exit = np.where(short_exits)[0] if short_exits is not None else []

    combined_short_indices = sorted(np.unique(np.concatenate([idx_short_entry, idx_short_exit])))

    # FIFO Simulation for Short positions
    for i in combined_short_indices:
        is_entry = short_entries.iloc[i] if short_entries is not None else False
        is_exit = short_exits.iloc[i] if short_exits is not None else False

        if is_entry:
            qty = entry_sizes.iloc[i]
            current_short_qty += qty
            size_series.iloc[i] = qty

        if is_exit:
            ratio = 1.0
            if exit_ratios is not None:
                ratio = exit_ratios.iloc[i]

            if current_short_qty > 0:
                if ratio >= 0.99:
                    exit_amt = current_short_qty
                else:
                    exit_amt = current_short_qty * ratio
                    exit_amt = max(1.0, round(exit_amt))
                    if exit_amt > current_short_qty:
                        exit_amt = current_short_qty

                size_series.iloc[i] = exit_amt
                current_short_qty -= exit_amt
            else:
                size_series.iloc[i] = 0.0

    # 5. Run Portfolio
    # If exec_price is available, use it (Topstep/Strategy specific), else use Close
    price_to_use = exec_price if exec_price is not None else data['Close']

    # Use high cash to simulate Margin/Futures (avoid Spot cap)
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
        # Note: sl_stop is disabled when exec_price is provided, as the strategy already manages
        # exit prices. VectorBT interprets sl_stop as a percentage by default, not absolute values,
        # which would cause incorrect calculations if we passed absolute distances.
        sl_stop=None
    )
    
    # 6. Metrics & Trades (Manual PnL Calculation using Strategy's exec_prices)
    #
    # IMPORTANT: VectorBT does NOT use exec_price for exit prices - it uses the actual
    # market close price. We must calculate PnL manually using the strategy's exec_prices.

    trades_df = pf.trades.records_readable

    # AGGREGATE TRADES by Entry Timestamp to handle Partials as Single Trade
    aggregated_trades = {}

    cumulative_pnl = 0.0
    equity_series = [req.initial_equity]

    # Build a lookup for exec_prices by timestamp for accurate exit prices
    # Use BOTH string and normalized formats to handle timezone differences
    exec_price_lookup = {}
    if exec_price is not None:
        for idx, val in exec_price.items():
            # Store with original string key
            exec_price_lookup[str(idx)] = float(val)
            # Also store with normalized timestamp (no timezone suffix)
            if hasattr(idx, 'strftime'):
                normalized_key = idx.strftime('%Y-%m-%d %H:%M:%S')
                exec_price_lookup[normalized_key] = float(val)

    # Process VBT records
    for _, row in trades_df.iterrows():
        entry_time_str = str(row['Entry Timestamp'])
        exit_time_str = str(row['Exit Timestamp'])

        # Also try normalized format for timestamps
        exit_timestamp = row['Exit Timestamp']
        entry_timestamp = row['Entry Timestamp']

        if hasattr(exit_timestamp, 'strftime'):
            exit_time_normalized = exit_timestamp.strftime('%Y-%m-%d %H:%M:%S')
        else:
            exit_time_normalized = str(exit_timestamp)[:19]  # First 19 chars: 'YYYY-MM-DD HH:MM:SS'

        if hasattr(entry_timestamp, 'strftime'):
            entry_time_normalized = entry_timestamp.strftime('%Y-%m-%d %H:%M:%S')
        else:
            entry_time_normalized = str(entry_timestamp)[:19]

        size = float(row['Size'])
        direction = row['Direction']  # 'Long' or 'Short'

        # Get entry price from our exec_price series for accuracy
        entry_price_trade = None
        if exec_price is not None:
            if entry_time_str in exec_price_lookup:
                entry_price_trade = exec_price_lookup[entry_time_str]
            elif entry_time_normalized in exec_price_lookup:
                entry_price_trade = exec_price_lookup[entry_time_normalized]

        if entry_price_trade is None:
            # Fallback to VBT's entry price
            entry_price_trade = float(row['Avg Entry Price'])

        # Get exit price from our exec_price series (NOT from VBT which uses market close)
        # VBT's 'Avg Exit Price' is the market close, not our SL/TP price
        # Try multiple lookup keys to handle timezone format differences
        exit_price_trade = None
        if exec_price is not None:
            if exit_time_str in exec_price_lookup:
                exit_price_trade = exec_price_lookup[exit_time_str]
            elif exit_time_normalized in exec_price_lookup:
                exit_price_trade = exec_price_lookup[exit_time_normalized]

        if exit_price_trade is None:
            # Fallback to VBT's exit price if exec_price not available
            exit_price_trade = float(row['Avg Exit Price'])
            logger.warning(f"exec_price lookup failed for exit at {exit_time_str}, using VBT price {exit_price_trade}")

        # Ensure prices are rounded to tick_size (safety net)
        def round_to_tick(price, ts):
            if ts > 0:
                return round(price / ts) * ts
            return price

        entry_price_trade = round_to_tick(entry_price_trade, tick_size)
        exit_price_trade = round_to_tick(exit_price_trade, tick_size)

        # Calculate PnL manually using correct prices
        if direction == 'Long':
            raw_pnl_points = exit_price_trade - entry_price_trade
        else:  # Short
            raw_pnl_points = entry_price_trade - exit_price_trade

        # Convert to dollar PnL: points * size * point_value
        gross_pnl = raw_pnl_points * size * point_value

        # Fee Deduction
        total_fee = fee_per_trade * size
        real_pnl = gross_pnl - total_fee

        if entry_time_str not in aggregated_trades:
            # New Trade Group
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
                "status": row['Status']
            }

        # Accumulate
        group = aggregated_trades[entry_time_str]
        group["net_pnl"] += real_pnl
        group["gross_pnl"] += gross_pnl
        group["fees"] += total_fee
        group["total_size"] += size

        # Weighted Avg Exit Price using our exec_price (not VBT's)
        group["exit_p_accum"] += (exit_price_trade * size)
        group["exit_size_accum"] += size

        # Update Exit Time to the latest one
        if row['Exit Timestamp'] > pd.to_datetime(group["exit_time"]):
             group["exit_time"] = exit_time_str
             group["status"] = row['Status']
             
    # Convert Aggregated Dict to List
    trades_list = []
    
    # We must sort by entry time to keep cumulative pnl correct
    # Keys are strings, but ISO format sorts correctly
    sorted_keys = sorted(aggregated_trades.keys())
    
    for k in sorted_keys:
        t = aggregated_trades[k]
        
        # Calculate Final Weighted Avg Exit
        avg_exit = 0.0
        if t["exit_size_accum"] > 0:
            avg_exit = t["exit_p_accum"] / t["exit_size_accum"]
            
        # Update Cumulative
        cumulative_pnl += t["net_pnl"]
        
        trades_list.append({
            "entry_time": t["entry_time"],
            "exit_time": t["exit_time"],
            "side": t["side"],
            "entry_price": t["entry_price"],
            "exit_price": avg_exit,
            "pnl": t["net_pnl"],
            "gross_pnl": t["gross_pnl"],
            "fees": t["fees"],
            "size": t["total_size"], # This is the TOTAL size closed (sum of parts) = Initial Size essentially
            "pnl_pct": (t["net_pnl"] / req.initial_equity) * 100,
            "status": t["status"],
            "session": get_session(t["entry_time"])
        })
        
        # Add point to equity curve at trade close
        equity_series.append(req.initial_equity + cumulative_pnl)
        
    # Re-calculate aggregates based on Real PnL
    total_trades = len(trades_list)
    winning_trades = [t for t in trades_list if t['pnl'] > 0]
    win_rate = (len(winning_trades) / total_trades * 100) if total_trades > 0 else 0.0
    total_return = (cumulative_pnl / req.initial_equity) * 100
    
    # Equity Curve Formatting
    # Use VBT equity for visual shape, but we might want to scale it to match final PnL?
    # Because VBT Equity doesn't include our custom Fees or Aggregation.
    # But Trade-based equity series (above) is coarse (only at exit).
    # Let's stick to Scaled VBT Equity as it's time-series based.
    
    vbt_equity = pf.value()
    adjusted_equity = req.initial_equity + (vbt_equity - sim_cash) * point_value
    
    # Correction: Deduct accumulated fees from equity curve?
    # Complex without loop. We accept Gross Equity Curve for visual, Net PnL for stats.
    
    equity_curve = [{"time": str(idx), "value": float(val)} for idx, val in adjusted_equity.items()]
    
    # Max Drawdown needs re-calc on adjusted series
    peak = adjusted_equity.cummax()
    drawdown = (adjusted_equity - peak) / peak
    max_drawdown = float(drawdown.min()) * 100

    metrics = {
        "total_return": float(total_return),
        "win_rate": float(win_rate),
        "total_trades": int(total_trades),
        "max_drawdown": float(max_drawdown),
        "sharpe_ratio": float(pf.sharpe_ratio()) 
    }
    
    # Sort trades by entry time
    trades_list.sort(key=lambda x: x["entry_time"]) 

    return {
        "metrics": metrics,
        "trades": trades_list,
        "equity_curve": equity_curve,
    }


# =============================================================================
# OPTIMIZATION ENDPOINTS
# =============================================================================

from concurrent.futures import ProcessPoolExecutor, as_completed
from uuid import uuid4
import itertools
import json
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
