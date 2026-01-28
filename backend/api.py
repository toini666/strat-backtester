import logging
import sys
import os
import inspect
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

import pandas as pd
import numpy as np
import vectorbt as vbt
import yfinance as yf
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, field_validator

# Configure module logger
logger = logging.getLogger(__name__)

# Add src to path to import strategies
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.strategies.base import Strategy
# from src.strategies.rob_reversal import RobReversal # Dynamically loaded now
from src.data.topstep import TopstepClient

router = APIRouter()
topstep = TopstepClient()

# --- Cache ---
TOPSTEP_CACHE = {
    "params": None, # (contract_id, interval, days)
    "data": None,
    "original_start_date": None
}

# --- Models ---

class BacktestRequest(BaseModel):
    """Request model for backtest with validation."""
    strategy_name: str = Field(..., min_length=1, description="Name of the strategy to run")
    ticker: str = Field(..., min_length=1, description="Ticker symbol")
    source: str = Field(default="Yahoo", pattern="^(Yahoo|Topstep)$", description="Data source: Yahoo or Topstep")
    contract_id: Optional[str] = Field(default=None, description="Contract ID (required for Topstep)")
    interval: str = Field(default="15m", pattern="^(1m|2m|5m|15m|30m|1h|4h|1d)$", description="Data interval")
    days: int = Field(default=14, ge=1, le=365, description="Number of days of historical data")
    params: Dict[str, Any] = Field(default_factory=dict, description="Strategy parameters")

    # Risk Management with validation
    initial_equity: float = Field(default=50000.0, ge=1000, le=10000000, description="Initial equity")
    risk_per_trade: float = Field(default=0.01, ge=0.001, le=0.1, description="Risk per trade (0.01 = 1%)")

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
    exit_time: str
    side: str
    entry_price: float
    exit_price: float
    pnl: float
    gross_pnl: float
    fees: float
    size: float
    pnl_pct: float
    status: str 
    session: str # Asia, UK, US, Outside

def get_session(dt_str: str) -> str:
    # Assuming dt_str is ISO format "YYYY-MM-DD HH:MM:SS"
    try:
        dt = pd.to_datetime(dt_str)
        # Using simple hour check (Timezone assumed UTC or Local as per data)
        # User defined sessions (assuming 24h format):
        # Asia: 00:00 - 08:59
        # UK: 09:00 - 15:29
        # US: 15:30 - 22:00
        # Outside: 22:01 - 23:59
        
        h = dt.hour
        m = dt.minute
        time_val = h * 60 + m
        
        # Asia: 0 -> 8:59 (0 -> 539)
        if 0 <= time_val < 540:
            return "Asia"
        
        # UK: 9:00 -> 15:29 (540 -> 929)
        if 540 <= time_val < 930:
            return "UK"
            
        # US: 15:30 -> 22:00 (930 -> 1320)
        # Logic says 22:00 is IN US session? "15h30 à 22h".
        # Usually implies up to 22:00:00 or end of 22:00?
        # Let's assume inclusive of 22:00 (1320) or up to 22:00 exclusive?
        # User said "exclude trades between 22h and midnight".
        # So US ends at 22:00.
        if 930 <= time_val <= 1320:
            return "US"
            
        return "Outside"
    except Exception as e:
        logger.warning(f"Failed to parse session from timestamp '{dt_str}': {e}")
        return "Unknown" 

class BacktestResult(BaseModel):
    metrics: Dict[str, Any]
    trades: List[Trade]
    equity_curve: List[Dict[str, Any]]

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

@router.get("/topstep/contracts")
def get_topstep_contracts():
    try:
        contracts = topstep.fetch_available_contracts()
        return [{
            "id": c["id"], 
            "name": c["name"], 
            "description": c.get("description", ""),
            "tick_size": c.get("tickSize"),
            "tick_value": c.get("tickValue")
        } for c in contracts]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

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
    "HG": 3.24, "MHG": 1.24, # Copper
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

@router.post("/backtest", response_model=BacktestResult)
def run_backtest(req: BacktestRequest):
    # Reload strategies to ensure code changes (like rounding/logic fixes) are picked up dynamically
    load_strategies()
    
    if req.strategy_name not in STRATEGIES:
        raise HTTPException(status_code=404, detail="Strategy not found")
    
    # 1. Fetch Data
    end_date = datetime.now()
    original_start_date = end_date - timedelta(days=req.days)
    
    # Warmup Logic
    # Always fetch extra 1000 bars to ensure indicator convergence for all strategies (EMA, RSI, HA, etc)
    warmup_bars = 1000
    
    start_date = original_start_date
    if warmup_bars > 0:
        # Approximate Lookback Calculation
        # We need to subtract N bars from original_start_date
        # Simple mapping
        map_min = {
            "1m": 1, "2m": 2, "5m": 5, "15m": 15, "30m": 30, "60m": 60, "1h": 60,
            "4h": 240, "1d": 1440 
        }
        
        minutes_per_bar = 15 # default
        if req.interval in map_min:
            minutes_per_bar = map_min[req.interval]
        elif req.interval.endswith('m'):
            try:
                minutes_per_bar = int(req.interval[:-1])
            except:
                pass
        elif req.interval.endswith('h'):
             try:
                minutes_per_bar = int(req.interval[:-1]) * 60
             except:
                pass
        elif req.interval.endswith('d'):
             try:
                minutes_per_bar = int(req.interval[:-1]) * 1440
             except:
                pass
                
        # Add 50% buffer for weekends/holidays if using Minute candles
        total_minutes = warmup_bars * minutes_per_bar * 1.5
        warmup_delta = timedelta(minutes=total_minutes)
        start_date = original_start_date - warmup_delta
        logger.info(f"Warmup Active: Fetching {warmup_bars} extra bars. Adjusted Start: {start_date}")

    try:
        data = pd.DataFrame()
        if req.source == "Topstep":
            if not req.contract_id:
                raise HTTPException(status_code=400, detail="Contract ID required for Topstep")
                
            # Check Cache
            current_params = (req.contract_id, req.interval, req.days)
            if TOPSTEP_CACHE["params"] == current_params and TOPSTEP_CACHE["data"] is not None:
                logger.info(f"Using cached Topstep data for {current_params}")
                data = TOPSTEP_CACHE["data"].copy()
                # Restore original_start_date to ensure consistent slicing (same window as first run)
                if TOPSTEP_CACHE["original_start_date"]:
                     original_start_date = TOPSTEP_CACHE["original_start_date"]
            else:
                data = topstep.fetch_historical_data(req.contract_id, start_date, end_date, req.interval)
                # Update Cache
                TOPSTEP_CACHE["params"] = current_params
                TOPSTEP_CACHE["data"] = data.copy()
                TOPSTEP_CACHE["original_start_date"] = original_start_date
        else:
            # Yahoo
            data = yf.download(req.ticker, start=start_date, end=end_date, interval=req.interval, progress=False, auto_adjust=True)
            if isinstance(data.columns, pd.MultiIndex):
                data.columns = data.columns.droplevel(1)
            
        if data.empty:
            raise HTTPException(status_code=400, detail=f"No data found for {req.ticker}")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Data fetch error: {str(e)}")

    # 2. Run Strategy on FULL DATA (including warmup)
    StrategyClass = STRATEGIES[req.strategy_name]
    strategy_instance = StrategyClass()
    params = strategy_instance.default_params.copy()
    params.update(req.params)
    
    # ... (Tick Size Logic omitted for brevity, assumed unchanged in context) ...
    # Auto-inject tick_size logic duplicated here just for context integration if needed,
    # but practically we should just keep the existing block. 
    # Since replace_file_content replaces a block, I must include the Tick Size logic or ensure I don't overwrite it bad.
    # The Block I am replacing ends at "except Exception as e: raise ... strategy execution error" (Line 348).
    # So I need to include the Tick Size Setup (Lines 264-292) and Simulation (295+).
    
    # RE-INSERT TICK SIZE LOGIC (Lines 264-292 from original)
    current_tick_size = 0.25 
    if req.source == "Topstep" and req.contract_id:
        try:
            contracts = topstep.fetch_available_contracts()
            contract = next((c for c in contracts if str(c['id']) == str(req.contract_id)), None)
            if contract:
                current_tick_size = float(contract.get('tickSize', 0.25))
            else:
                 sorted_spec_keys = sorted(CONTRACT_SPECS.keys(), key=len, reverse=True)
                 for k in sorted_spec_keys:
                    if req.ticker and k in req.ticker.upper():
                         pass
        except:
            pass
    else:
        sorted_spec_keys = sorted(CONTRACT_SPECS.keys(), key=len, reverse=True)
        for k in sorted_spec_keys:
            if k in req.ticker.upper():
                current_tick_size = CONTRACT_SPECS[k]['tick_size']
                break
    
    params['tick_size'] = current_tick_size
    
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

        # --- Topstep Time Filter (22:00 - 00:00 Paris Time) ---
        if req.source == "Topstep":
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

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Strategy execution error: {str(e)}")

    # 4. Position Sizing & Contract Specs
    # We will build a Size Series for VectorBT
    size_series = pd.Series(0.0, index=data.index)
    point_value = 1.0 # Default
    tick_size = 0.25 # Default
    tick_value = 12.5 # Default (ES/NQ standard if unknown)
    
    fee_per_trade = 0.0
    
    if req.source == "Topstep" and req.contract_id:
        try:
            contracts = topstep.fetch_available_contracts()
            contract = next((c for c in contracts if str(c['id']) == str(req.contract_id)), None)
            
            if contract:
                tick_size = float(contract.get('tickSize', 0.25))
                tick_value = float(contract.get('tickValue', 5.0))
                contract_name = contract.get('name', '').upper()
                
                # Point Value calculation
                if tick_size > 0:
                    point_value = tick_value / tick_size
                    
                # Fee Determination
                # Check for matches in FEES_MAP keys
                # Sort keys by length desc to match "MNQ" before "NQ" if needed (though "M" prefix usually distinct)
                sorted_keys = sorted(FEES_MAP.keys(), key=len, reverse=True)
                for k in sorted_keys:
                    # Crude check: if key is in name. e.g. "MNQ" in "MNQH6"
                    if k in contract_name:
                        fee_per_trade = FEES_MAP[k]
                        break

            # Override with Hardcoded Specs if available (More reliable)
            # Check matches in CONTRACT_SPECS
            sorted_spec_keys = sorted(CONTRACT_SPECS.keys(), key=len, reverse=True)
            for k in sorted_spec_keys:
                if contract and k in contract.get('name', '').upper():
                    spec = CONTRACT_SPECS[k]
                    tick_size = spec['tick_size']
                    tick_value = spec['tick_value']
                    if tick_size > 0:
                         point_value = tick_value / tick_size
                    break
        except Exception as e:
            logger.warning(f"Contract spec fetch failed: {e}")
            
    # Calculate Base Sizing (Entries)
    risk_amount = req.initial_equity * req.risk_per_trade
    
    # If strategy provided specific SL distances, use them
    if sl_dist_series is not None:
        safe_sl = sl_dist_series.replace(0, tick_size)
        
        # Ensure positive distance (Reciprocity: Short dist should be positive)
        safe_sl = safe_sl.abs() 
        
        sl_ticks = safe_sl / tick_size
        raw_sizes = risk_amount / (sl_ticks * tick_value)
        
        # Round down to nearest int, min 1
        entry_sizes = np.maximum(1.0, np.floor(raw_sizes)).fillna(1.0)
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
                         entry_sizes.iloc[idx] = max(1.0, float(int(calc_size)))
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
                         entry_sizes.iloc[idx] = max(1.0, float(int(calc_size)))
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
    
    return {
        "metrics": metrics,
        "trades": trades_list,
        "equity_curve": equity_curve
    }
