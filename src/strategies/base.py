from abc import ABC, abstractmethod
import pandas as pd
import numpy as np
from typing import Tuple, Dict, Any, Optional
from .indicators import Indicators

class Strategy(ABC):
    """
    Base class for all trading strategies.
    Uses pandas-ta for indicators.
    """
    
    name: str = "BaseStrategy"
    default_params: Dict[str, Any] = {}
    param_ranges: Dict[str, Any] = {}
    manual_exit: bool = False # If True, API wont pass SL/TP to VBT engine for execution (still used for sizing)
    use_simulator: bool = False
    simulator_settings: Dict[str, Any] = {}
    blackout_sensitive: bool = False
    
    def __init__(self):
        # Ensure indicators are loaded
        Indicators.ensure_ta_extensions()
        
    @abstractmethod
    def generate_signals(
        self, 
        data: pd.DataFrame,
        params: Dict[str, Any] = None
    ) -> Tuple[pd.Series, pd.Series]:
        """
        Generate entry and exit signals.
        
        Args:
            data: DataFrame with OHLCV data
            params: Dictionary of strategy parameters (optional)
            
        Returns:
            Tuple of (entries, exits) as boolean pd.Series
        """
        pass
    
    def get_stop_loss(
        self, 
        data: pd.DataFrame, 
        entry_idx: int,
        params: Dict[str, Any] = None
    ) -> Optional[float]:
        """
        Calculate stop loss price for a specific entry.
        Override this method to implement dynamic stop loss.
        """
        return None
    
    def get_take_profit(
        self, 
        data: pd.DataFrame, 
        entry_idx: int,
        params: Dict[str, Any] = None
    ) -> Optional[float]:
        """
        Calculate take profit price for a specific entry.
        Override this method to implement dynamic take profit.
        """
        return None
        
    def get_params(self, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Merge provided params with defaults."""
        p = self.default_params.copy()
        if params:
            p.update(params)
        return p

    def get_simulator_settings(self, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Return simulator-specific behavior overrides for this strategy."""
        settings = self.simulator_settings.copy()
        return settings
