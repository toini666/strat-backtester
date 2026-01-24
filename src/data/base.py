from abc import ABC, abstractmethod
import pandas as pd
from datetime import datetime
from typing import Optional

class DataProvider(ABC):
    """
    Abstract base class for data providers.
    """
    
    @abstractmethod
    def fetch(
        self,
        symbol: str,
        start: datetime,
        end: datetime,
        timeframe: str = "1d"
    ) -> pd.DataFrame:
        """
        Fetch historical OHLCV data.
        
        Args:
            symbol: Ticker symbol (e.g. "MNQ", "BTC-USD")
            start: Start date
            end: End date
            timeframe: Candle timeframe (e.g. "1m", "5m", "1h", "1d")
            
        Returns:
            pd.DataFrame with columns: Open, High, Low, Close, Volume
            Index should be DatetimeIndex
        """
        pass
