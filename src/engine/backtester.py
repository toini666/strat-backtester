import vectorbt as vbt
import pandas as pd
import numpy as np
from ..strategies.base import Strategy
from ..risk.position_sizer import RiskBasedPositionSizer
from dataclasses import dataclass

@dataclass
class BacktestResult:
    """Wrapper for VectorBT Portfolio and results."""
    portfolio: vbt.Portfolio
    data: pd.DataFrame
    strategy: Strategy
    
    @property
    def total_return(self) -> float:
        return self.portfolio.total_return()
        
    @property
    def sharpe_ratio(self) -> float:
        return self.portfolio.sharpe_ratio()
        
    @property
    def max_drawdown(self) -> float:
        return self.portfolio.max_drawdown()
        
    @property
    def win_rate(self) -> float:
        return self.portfolio.win_rate()
    
    @property
    def profit_factor(self) -> float:
        return self.portfolio.profit_factor()
        
    @property
    def total_trades(self) -> int:
        return self.portfolio.total_trades()

class Backtester:
    """
    Backtesting engine using VectorBT.
    """
    
    # Contract specs (Symbol -> {tick_size, tick_value, point_value})
    FUTURES_SPECS = {
        "MNQ": {"tick_size": 0.25, "tick_value": 0.50, "point_value": 2.0},
        "MES": {"tick_size": 0.25, "tick_value": 1.25, "point_value": 5.0},
        "MYM": {"tick_size": 1.0, "tick_value": 0.50, "point_value": 0.5},
        "MGC": {"tick_size": 0.10, "tick_value": 1.00, "point_value": 10.0},
        # Crypto defaults to 1.0 (pass 'point_value' 1.0 if not found)
    }
    
    def __init__(
        self,
        initial_capital: float = 10000.0,
        commission: float = 0.0,      # Fixed amount per contract/trade usually, or %? VBT uses ratio by default
        slippage: float = 0.0,        # As ratio or fixed? VBT standard is ratio or fixed? 
                                      # VBT 'slippage' argument is usually pct of price (ratio).
        risk_per_trade: float = 0.01
    ):
        self.initial_capital = initial_capital
        self.commission = commission
        self.slippage = slippage
        self.risk_per_trade = risk_per_trade
        self.position_sizer = RiskBasedPositionSizer(risk_per_trade)
        
    def get_specs(self, symbol: str) -> dict:
        # Heuristic to find specs (handle MNQZ4 etc)
        for root, specs in self.FUTURES_SPECS.items():
            if symbol.startswith(root):
                return specs
        return {"point_value": 1.0}
        
    def run(
        self,
        data: pd.DataFrame,
        strategy: Strategy,
        params: dict = None,
        symbol: str = "UNKNOWN"
    ) -> BacktestResult:
        """
        Execute backtest.
        """
        # 1. Generate signals
        entries, exits = strategy.generate_signals(data, params)
        
        # 2. Calculate Sizing
        # We need to iterate or vector-calculate size. 
        # For simplicity and correctness with dynamic StopLoss, let's iterate 
        # (or map) over the entry points.
        # Since we want to support backtesting, speed is key, but exact sizing is critical.
        
        specs = self.get_specs(symbol)
        point_value = specs["point_value"]
        
        # Initialize size array (all zeros)
        # Note: VBT wants size at the moment of entry.
        size = pd.Series(0, index=data.index, dtype=float)
        
        # For this implementation, we simply loop over entries to calculate SL and Size.
        # Optimization: Only calculate for True entries.
        entry_indices = np.where(entries)[0]
        
        # Get stop loss logic (assuming strategy implements get_stop_loss or we default to fixed % if not)
        # To avoid slow loop, we can try to vectorize calculate "Proposed Size".
        # But `get_stop_loss` might be complex.
        # Let's assume strategy provides `get_stop_loss` which returns a scalar price.
        
        # We'll allow loose vectorization by pre-calculating common logic if possible.
        # But for 'examples', get_stop_loss uses `iloc`.
        
        # Quick Loop
        for idx in entry_indices:
            try:
                sl_price = strategy.get_stop_loss(data, idx, params)
                if sl_price is None:
                    # Default: Use parameters if available or fallback
                    # This fallback should be better handled, but for now safely default 1 unit
                    num_contracts = 1
                else:
                    entry_price = data['Close'].iloc[idx] # Use Close as entry approximation
                    num_contracts = self.position_sizer.calculate_size(
                        capital=self.initial_capital, # Note: Uses Fixed Initial Capital for sizing (non-compounding) implementation for simplicity
                        entry_price=entry_price,
                        stop_loss_price=sl_price,
                        point_value=point_value
                    )
                
                # VBT Size = NumContracts * PointValue
                size.iloc[idx] = num_contracts * point_value
                
            except Exception as e:
                print(f"Error calculating size at idx {idx}: {e}")
                size.iloc[idx] = 1.0 # Fallback
                
        # 3. Run VectorBT
        # fees: VBT fees is typically ratio. If we want fixed per contract:
        # fees = commission (per contract) / point_value ?
        # Actually VBT `fees` is per-dollar if fixed? No, "If fees is a single float, it's a percentage."
        # If we want fixed fees, we need `fees` array or different setup.
        # For MVP, let's ignore commission or treat as ratio (e.g. 0.001)
        
        pf = vbt.Portfolio.from_signals(
            close=data['Close'],
            entries=entries,
            exits=exits,
            size=size,
            size_type='amount', # We provide absolute amount (contracts * pv)
            init_cash=self.initial_capital,
            fees=self.commission, # Assuming this is ratio for now if < 1, or need to check VBT docs for fixed.
            slippage=self.slippage,
            freq='1min' # Should be dynamic based on data
        )
        
        return BacktestResult(pf, data, strategy)
