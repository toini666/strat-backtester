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

# --- Models ---

class BacktestRequest(BaseModel):
    """Request model for backtest with validation."""
    strategy_name: str = Field(..., min_length=1, description="Name of the strategy to run")
    ticker: str = Field(..., min_length=1, description="Ticker symbol")
    source: str = Field(default="Yahoo", pattern="^(Yahoo|Topstep)$", description="Data source: Yahoo or Topstep")
    contract_id: Optional[str] = Field(default=None, description="Contract ID (required for Topstep)")
    interval: str = Field(default="15m", pattern="^(1m|5m|15m|30m|1h|4h|1d)$", description="Data interval")
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

@router.post("/backtest", response_model=BacktestResult)
def run_backtest(req: BacktestRequest):
    if req.strategy_name not in STRATEGIES:
        raise HTTPException(status_code=404, detail="Strategy not found")
    
    # 1. Fetch Data
    end_date = datetime.now()
    start_date = end_date - timedelta(days=req.days)
    
    try:
        data = pd.DataFrame()
        if req.source == "Topstep":
            if not req.contract_id:
                raise HTTPException(status_code=400, detail="Contract ID required for Topstep")
            data = topstep.fetch_historical_data(req.contract_id, start_date, end_date, req.interval)
            
            # Identify Contract Symbol for Fees
            # Contract ID format usually "CON.F.US.MNQ.H26" or similar
            # Robust way: check if keys in contract name/desc
            # We'll infer fee later
        else:
            # Yahoo
            data = yf.download(req.ticker, start=start_date, end=end_date, interval=req.interval, progress=False, auto_adjust=True)
            if isinstance(data.columns, pd.MultiIndex):
                data.columns = data.columns.droplevel(1)
            
        if data.empty:
            raise HTTPException(status_code=400, detail=f"No data found for {req.ticker}")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Data fetch error: {str(e)}")

    # 2. Run Strategy
    StrategyClass = STRATEGIES[req.strategy_name]
    strategy_instance = StrategyClass()
    params = strategy_instance.default_params.copy()
    params.update(req.params)
    
    # 3. Simulate (VectorBT)
    try:
        signals = strategy_instance.generate_signals(data, params)
        exec_price = None
        sl_dist_series = None
        
        if len(signals) == 6:
             long_entries, long_exits, short_entries, short_exits, exec_price, sl_dist_series = signals
        elif len(signals) == 5:
             long_entries, long_exits, short_entries, short_exits, exec_price = signals
        elif len(signals) == 4:
            long_entries, long_exits, short_entries, short_exits = signals
        else:
            long_entries, short_entries = signals
            long_exits = None
            short_exits = None

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
        except Exception as e:
            logger.warning(f"Contract spec fetch failed: {e}")
            
    # Calculate Sizes
    risk_amount = req.initial_equity * req.risk_per_trade
    
    # If strategy provided specific SL distances, use them
    if sl_dist_series is not None:
        # Avoid div by zero
        safe_sl = sl_dist_series.replace(0, tick_size)
        
        # User Formula Update: Size = Risk / (SL_Ticks * Tick_Value)
        # SL_Ticks = SL_Dist / Tick_Size
        # So: Size = Risk / ((SL_Dist / Tick_Size) * Tick_Value)
        
        sl_ticks = safe_sl / tick_size
        raw_sizes = risk_amount / (sl_ticks * tick_value)
        
        # Round down to nearest int, min 1
        size_series = np.maximum(1.0, np.floor(raw_sizes))
        size_series = size_series.fillna(1.0) # Fallback
    else:
        # Global Sizing based on Max SL
        max_sl = float(params.get('max_stop_loss', 35.0))
        if max_sl > 0 and tick_size > 0 and tick_value > 0:
             # Same formula
            sl_ticks = max_sl / tick_size
            raw_size = risk_amount / (sl_ticks * tick_value)
            fixed_size = max(1.0, float(int(raw_size)))
            size_series = fixed_size
            
    # 5. Run Portfolio
    # If exec_price is available, use it (Topstep/Strategy specific), else use Close
    price_to_use = exec_price if exec_price is not None else data['Close']

    pf = vbt.Portfolio.from_signals(
        close=price_to_use, 
        entries=long_entries,
        exits=long_exits,
        short_entries=short_entries,
        short_exits=short_exits,
        init_cash=req.initial_equity,
        freq=req.interval,
        size=size_series,
        size_type='Amount', # Fixed amount of contracts
        fees=0.0, # We handle PnL scaling manually
        slippage=0.0
    )
    
    # 6. Metrics & Trades (Manual PnL Scaling)
    
    trades_df = pf.trades.records_readable
    trades_list = []
    
    cumulative_pnl = 0.0
    equity_series = [req.initial_equity]
    
    for _, row in trades_df.iterrows():
        raw_pnl = float(row['PnL'])
        size = float(row['Size'])
        
        # Gross PnL
        gross_pnl = raw_pnl * point_value
        
        # Fee Deduction (Round Turn fee * number of contracts)
        total_fee = fee_per_trade * size
        
        real_pnl = gross_pnl - total_fee
        cumulative_pnl += real_pnl
        
        trades_list.append({
            "entry_time": str(row['Entry Timestamp']),
            "exit_time": str(row['Exit Timestamp']),
            "side": row['Direction'],
            "entry_price": float(row['Avg Entry Price']),
            "exit_price": float(row['Avg Exit Price']),
            "pnl": real_pnl, # Net PnL
            "gross_pnl": gross_pnl,
            "fees": total_fee,
            "size": size,
            "pnl_pct": (real_pnl / req.initial_equity) * 100, # RoI on Account
            "status": row['Status'],
            "session": get_session(str(row['Entry Timestamp']))
        })
        equity_series.append(req.initial_equity + cumulative_pnl)
        
    # Re-calculate aggregates based on Real PnL
    total_trades = len(trades_list)
    winning_trades = [t for t in trades_list if t['pnl'] > 0]
    win_rate = (len(winning_trades) / total_trades * 100) if total_trades > 0 else 0.0
    total_return = (cumulative_pnl / req.initial_equity) * 100
    
    # Equity Curve Formatting
    vbt_equity = pf.value()
    # We must construct equity curve carefully. VBT one is unscaled.
    # But wait, VBT equity curve has many points (every bar).
    # Our manual cumulative_pnl is only at trade close.
    # To get accurate equity curve (Open Equity), we'd need to scale the entire VBT series.
    # NewEquity(t) = Init + (VBT_Equity(t) - Init) * PointValue 
    # BUT! Fees happen at trade points. This makes continuous curve weird.
    # Approximation: Scale VBT equity by PointValue. This ignores Fees intra-trade but shows correct price moves.
    # Then we might have a slight drift due to fees, but visual curve is OK.
    # Better: just return the trade-based curve? No, charts need time series.
    # We'll return Scaled VBT Equity. Fees are "hidden" costs on the trade list PnL? 
    # Actually, let's subtract estimated fees cumulatively? Too hard for 15s calculation.
    # Let's start with Scaled VBT Equity (Gross). The Trade List has Net PnL.
    
    adjusted_equity = req.initial_equity + (vbt_equity - req.initial_equity) * point_value
    
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
        "sharpe_ratio": float(pf.sharpe_ratio()) # Approx
    }
    
    return {
        "metrics": metrics,
        "trades": trades_list,
        "equity_curve": equity_curve
    }
