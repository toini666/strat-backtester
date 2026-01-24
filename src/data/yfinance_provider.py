import yfinance as yf
import pandas as pd
from datetime import datetime
from .base import DataProvider

class YFinanceProvider(DataProvider):
    """
    Fetches historical data from Yahoo Finance.
    """
    
    def fetch(
        self,
        symbol: str,
        start: datetime,
        end: datetime,
        timeframe: str = "1d"
    ) -> pd.DataFrame:
        """
        Fetch data from yfinance.
        """
        # yfinance interval format: 1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, 1d, 5d, 1wk, 1mo, 3mo
        # Our internal format is compatible (1m, 5m, 1h, 1d)
        
        df = yf.download(
            tickers=symbol,
            start=start,
            end=end,
            interval=timeframe,
            progress=False,
            auto_adjust=False  # We want pure OHLC, maybe adjusted close separately if needed
        )
        
        # yfinance returns MultiIndex columns if multiple tickers, but we expect one.
        if isinstance(df.columns, pd.MultiIndex):
            df = df.xs(symbol, axis=1, level=1)
            
        # Basic cleanup
        # Ensure we have Open, High, Low, Close, Volume
        expected_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
        df = df[expected_cols]
        
        return df
