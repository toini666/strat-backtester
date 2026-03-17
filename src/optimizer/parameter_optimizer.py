"""
Parameter Optimizer with Session Combinations and Parallelization.

This module extends the basic grid search to support:
- Custom parameter ranges (not just from strategy.param_ranges)
- Session combination testing (all 2^n-1 non-empty subsets)
- Parallel execution using multiprocessing
- Progress tracking via callback
"""

import itertools
import json
import os
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Dict, Any, List, Optional, Callable, Tuple
from pathlib import Path

import pandas as pd
import numpy as np


# Session definitions – reference-frame boundaries (matching api.py / simulator.py)
SESSIONS = {
    "Asia": (0, 540),      # 00:00 - 08:59
    "UK": (540, 930),      # 09:00 - 15:29
    "US": (930, 1440),     # 15:30 - end of day
}


@dataclass
class ParameterRange:
    """Definition of a parameter range for optimization."""
    name: str
    values: List[Any]
    param_type: str = "float"  # "float", "int", "bool"

    @property
    def count(self) -> int:
        return len(self.values)

    @classmethod
    def from_min_max_step(cls, name: str, min_val: float, max_val: float, step: float, param_type: str = "float") -> 'ParameterRange':
        """Create a ParameterRange from min/max/step specification."""
        if param_type == "int":
            values = list(range(int(min_val), int(max_val) + 1, int(step)))
        else:
            values = []
            current = min_val
            while current <= max_val + 1e-9:  # Small epsilon for float comparison
                values.append(round(current, 6))
                current += step
        return cls(name=name, values=values, param_type=param_type)


@dataclass
class OptimizationConfig:
    """Configuration for an optimization run."""
    strategy_name: str
    parameters: List[ParameterRange]
    sessions: List[str]  # e.g., ["Asia", "UK", "US"]

    # Data config
    contract_id: Optional[str] = None
    ticker: str = "BTC-USD"
    source: str = "Topstep"
    interval: str = "15m"
    days: int = 14

    # Risk config
    initial_equity: float = 50000.0
    risk_per_trade: float = 0.01

    @property
    def param_combinations_count(self) -> int:
        """Number of parameter combinations."""
        if not self.parameters:
            return 1
        return int(np.prod([p.count for p in self.parameters]))

    @property
    def session_combinations(self) -> List[List[str]]:
        """Generate all non-empty subsets of sessions."""
        combos = []
        for r in range(1, len(self.sessions) + 1):
            for combo in itertools.combinations(self.sessions, r):
                combos.append(list(combo))
        return combos

    @property
    def session_combinations_count(self) -> int:
        """Number of session combinations (2^n - 1)."""
        return (2 ** len(self.sessions)) - 1 if self.sessions else 1

    @property
    def total_combinations(self) -> int:
        """Total number of backtests to run."""
        return self.param_combinations_count * max(1, self.session_combinations_count)


@dataclass
class OptimizationResultSummary:
    """Summary of a single optimization result (for persistence)."""
    rank: int
    parameters: Dict[str, Any]
    sessions: List[str]
    total_return: float
    win_rate: float
    trade_count: int
    max_drawdown: float


@dataclass
class OptimizationRunSummary:
    """Summary of an optimization run (for persistence)."""
    id: str
    timestamp: str
    strategy_name: str
    contract_id: Optional[str]
    ticker: str
    source: str
    interval: str
    days: int
    parameter_ranges: Dict[str, Dict[str, Any]]
    sessions_tested: List[str]
    total_combinations_tested: int
    top_results: List[OptimizationResultSummary]

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "strategy_name": self.strategy_name,
            "contract_id": self.contract_id,
            "ticker": self.ticker,
            "source": self.source,
            "interval": self.interval,
            "days": self.days,
            "parameter_ranges": self.parameter_ranges,
            "sessions_tested": self.sessions_tested,
            "total_combinations_tested": self.total_combinations_tested,
            "top_results": [asdict(r) for r in self.top_results]
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'OptimizationRunSummary':
        """Create from dictionary."""
        top_results = [OptimizationResultSummary(**r) for r in data.get("top_results", [])]
        return cls(
            id=data["id"],
            timestamp=data["timestamp"],
            strategy_name=data["strategy_name"],
            contract_id=data.get("contract_id"),
            ticker=data.get("ticker", ""),
            source=data.get("source", "Topstep"),
            interval=data.get("interval", "15m"),
            days=data.get("days", 14),
            parameter_ranges=data.get("parameter_ranges", {}),
            sessions_tested=data.get("sessions_tested", []),
            total_combinations_tested=data.get("total_combinations_tested", 0),
            top_results=top_results
        )


def get_session_from_time(dt: pd.Timestamp) -> str:
    """Determine session from timestamp (DST-aware)."""
    from src.engine.simulator import _to_ref_minutes
    ref = _to_ref_minutes(dt)
    if ref < 540:
        return "Asia"
    if ref < 930:
        return "UK"
    return "US"


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
        dd = (peak - cumulative) / initial_equity if initial_equity > 0 else 0
        if dd > max_dd:
            max_dd = dd

    return {
        "total_return": (total_pnl / initial_equity * 100) if initial_equity > 0 else 0.0,
        "win_rate": win_rate,
        "trade_count": len(trades),
        "max_drawdown": -max_dd * 100  # Negative percentage
    }


class OptimizationHistoryManager:
    """Manages persistence of optimization history."""

    def __init__(self, history_file: Optional[str] = None):
        if history_file:
            self.history_file = Path(history_file)
        else:
            # Default location
            home = Path.home()
            config_dir = home / ".nebular-apollo"
            config_dir.mkdir(exist_ok=True)
            self.history_file = config_dir / "optimization_history.json"

    def load_history(self) -> List[OptimizationRunSummary]:
        """Load optimization history from file."""
        if not self.history_file.exists():
            return []

        try:
            with open(self.history_file, 'r') as f:
                data = json.load(f)
            return [OptimizationRunSummary.from_dict(item) for item in data]
        except Exception as e:
            print(f"Error loading optimization history: {e}")
            return []

    def save_run(self, run: OptimizationRunSummary) -> None:
        """Save an optimization run to history."""
        history = self.load_history()
        history.append(run)

        # Keep only last 100 runs to limit file size
        if len(history) > 100:
            history = history[-100:]

        with open(self.history_file, 'w') as f:
            json.dump([r.to_dict() for r in history], f, indent=2)

    def get_run(self, run_id: str) -> Optional[OptimizationRunSummary]:
        """Get a specific run by ID."""
        history = self.load_history()
        for run in history:
            if run.id == run_id:
                return run
        return None

    def delete_run(self, run_id: str) -> bool:
        """Delete a run from history."""
        history = self.load_history()
        new_history = [r for r in history if r.id != run_id]

        if len(new_history) == len(history):
            return False

        with open(self.history_file, 'w') as f:
            json.dump([r.to_dict() for r in new_history], f, indent=2)
        return True


def generate_param_combinations(parameters: List[ParameterRange]) -> List[Dict[str, Any]]:
    """Generate all parameter combinations."""
    if not parameters:
        return [{}]

    keys = [p.name for p in parameters]
    values = [p.values for p in parameters]

    combinations = []
    for combo in itertools.product(*values):
        combinations.append(dict(zip(keys, combo)))

    return combinations


def run_single_backtest(args: Tuple) -> Optional[Dict]:
    """
    Run a single backtest with given parameters.
    This function is designed to be called in a separate process.

    Args is a tuple: (params, sessions, config_dict, backtest_func_module_path)
    """
    params, sessions, config_dict, data_json = args

    try:
        # Import here to avoid pickling issues
        import pandas as pd
        import sys
        import os

        # Reconstruct data from JSON
        data = pd.read_json(data_json, orient='split')
        data.index = pd.to_datetime(data.index)

        # Import strategy and run backtest
        # This is a simplified version - in production, you'd call the actual backtest API
        from src.strategies.base import Strategy
        # TODO: Refactor to use event-driven simulator instead of legacy VectorBT Backtester
        # from src.engine.backtester import Backtester

        # Dynamic strategy loading
        strategy_name = config_dict['strategy_name']

        # Import the strategy class dynamically
        import importlib.util
        strategies_path = os.path.join(os.path.dirname(__file__), '..', 'strategies')

        # Find and load strategy
        for file_name in os.listdir(strategies_path):
            if file_name.endswith(".py") and file_name not in ["__init__.py", "base.py", "indicators.py"]:
                file_path = os.path.join(strategies_path, file_name)
                spec = importlib.util.spec_from_file_location(f"strategy_{file_name[:-3]}", file_path)
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)

                    import inspect
                    for name, obj in inspect.getmembers(module):
                        if inspect.isclass(obj) and issubclass(obj, Strategy) and obj is not Strategy:
                            if name == strategy_name:
                                StrategyClass = obj
                                break

        # Run backtest
        strategy = StrategyClass()
        backtester = Backtester(
            initial_capital=config_dict['initial_equity'],
            risk_per_trade=config_dict['risk_per_trade']
        )

        result = backtester.run(data, strategy, params=params)

        # Extract metrics
        return {
            "params": params,
            "sessions": sessions,
            "total_return": result.total_return,
            "win_rate": result.win_rate,
            "trade_count": result.total_trades,
            "max_drawdown": result.max_drawdown,
        }

    except Exception as e:
        print(f"Error in backtest: {e}")
        return None
