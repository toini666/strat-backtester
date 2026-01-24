import itertools
import pandas as pd
import numpy as np
from typing import Dict, Any, Type, List
from tqdm.auto import tqdm
import plotly.express as px

from ..strategies.base import Strategy
from ..engine.backtester import Backtester, BacktestResult

class GridSearchOptimizer:
    """
    Parameter optimization using Grid Search.
    
    Iterates through all combinations of parameter ranges, 
    runs backtest, and collects metrics.
    """
    
    def __init__(self, backtester: Backtester):
        self.backtester = backtester
        
    def optimize(
        self,
        data: pd.DataFrame,
        strategy_class: Type[Strategy],
        metric: str = "sharpe_ratio",
        symbol: str = "UNKNOWN"
    ) -> 'OptimizationResult':
        """
        Run grid search.
        
        Args:
           data: Historical data
           strategy_class: Strategy class to instantiate
           metric: Target metric to maximize
           symbol: Symbol for contract specs
        """
        # Instantiate dummy to get param ranges
        dummy_strat = strategy_class()
        ranges = dummy_strat.param_ranges
        
        if not ranges:
            print("No parameter ranges defined for optimization.")
            return None
            
        # Generate all combinations
        keys = ranges.keys()
        values = ranges.values()
        combinations = list(itertools.product(*values))
        
        print(f"Optimizing {len(combinations)} combinations...")
        
        results = []
        
        for combo in tqdm(combinations):
            params = dict(zip(keys, combo))
            
            # Instantiate strategy with these params? 
            # Or just pass params to generate_signals if supported.
            # Our Strategy.generate_signals takes params dict.
            # But Backtester.run takes instances.
            # Let's use the instance method pattern from backtester design.
            
            strat = strategy_class()
            # Run backtest
            try:
                res = self.backtester.run(data, strat, params=params, symbol=symbol)
                
                # Collect metrics
                metrics = {
                    "total_return": res.total_return,
                    "sharpe_ratio": res.sharpe_ratio,
                    "max_drawdown": res.max_drawdown,
                    "win_rate": res.win_rate,
                    "profit_factor": res.profit_factor,
                    "total_trades": res.total_trades
                }
                
                # Add params to result
                record = {**params, **metrics}
                results.append(record)
                
            except Exception as e:
                print(f"Error with params {params}: {e}")
                
        results_df = pd.DataFrame(results)
        return OptimizationResult(results_df, metric)

class OptimizationResult:
    """Container for optimization results."""
    
    def __init__(self, df: pd.DataFrame, target_metric: str):
        self.df = df
        self.target_metric = target_metric
        
    @property
    def best_result(self) -> pd.Series:
        """Row with best metric."""
        if self.df.empty:
            return pd.Series()
        return self.df.loc[self.df[self.target_metric].idxmax()]
        
    @property
    def best_params(self) -> dict:
        """Best parameters dict."""
        res = self.best_result
        if res.empty:
            return {}
        # Identify param cols? 
        # It's all cols that are passed in logic. 
        # But we mixed params and metrics.
        # Ideally we know which are params.
        # For MVP, we return the whole series dict or user filters.
        # But we can try to filter out known metrics.
        metrics_cols = ["total_return", "sharpe_ratio", "max_drawdown", "win_rate", "profit_factor", "total_trades"]
        return {k: v for k, v in res.to_dict().items() if k not in metrics_cols}
        
    @property
    def best_metric(self) -> float:
        return self.best_result[self.target_metric]
    
    def plot_heatmap(self, x_param: str, y_param: str, metric: str = None):
        """Plot heatmap of 2 params vs metric."""
        m = metric or self.target_metric
        if x_param not in self.df.columns or y_param not in self.df.columns:
            print(f"Params {x_param}, {y_param} not in results.")
            return None
            
        pivot = self.df.pivot_table(values=m, index=y_param, columns=x_param)
        fig = px.imshow(
            pivot, 
            title=f"{m} by {x_param} vs {y_param}",
            labels=dict(x=x_param, y=y_param, color=m),
            aspect="auto",
            origin='lower'
        )
        return fig
