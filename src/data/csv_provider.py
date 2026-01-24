import pandas as pd
from datetime import datetime
from .base import DataProvider

class CSVProvider(DataProvider):
    """
    Loads historical data from a local CSV file.
    """
    
    def __init__(self, file_path: str):
        self.file_path = file_path
        
    def fetch(
        self,
        symbol: str, # Unused for single file, or could be used to filter if CSV has symbol col
        start: datetime,
        end: datetime,
        timeframe: str = "1d" # Unused, assumes CSV matches desired timeframe
    ) -> pd.DataFrame:
        """
        Load data from CSV.
        """
        df = pd.read_csv(self.file_path)
        
        # Ensure Date column exists and set index
        if 'Date' in df.columns:
            df['Date'] = pd.to_datetime(df['Date'])
            df.set_index('Date', inplace=True)
        elif 'Time' in df.columns:
             df['Time'] = pd.to_datetime(df['Time'])
             df.set_index('Time', inplace=True)
             df.index.name = 'Date'
             
        # Filter by date range
        mask = (df.index >= start) & (df.index <= end)
        df = df.loc[mask]
        
        return df
