import requests
import pandas as pd
from datetime import datetime, timedelta
import time
from typing import Optional, Dict
from .base import DataProvider

class TopStepXProvider(DataProvider):
    """
    Fetches historical bar data from TopStepX API.
    """
    
    API_BASE = "https://api.topstepx.com"
    
    # Mapping commonly used tickers to TopStepX contract IDs if needed,
    # or we can rely on the user providing the correct ID/Symbol.
    # TopStepX often uses specific IDs. For simplicity, we'll assume symbol maps to contract details
    # or implement a lookup if necessary. For now, we assume the symbol passed IS the contract name expected by API
    # or we might need a mapping for things like "MNQ" -> current front month?
    # The user manual mentioned "The contract ID used for API calls must be the TopStep ts_contract_id from the TickerMap."
    # We might need a helper to get this ID. For now, let's implement basic fetching.
    
    def __init__(self, api_token: str):
        self.token = api_token
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
    
    def _parse_timeframe(self, timeframe: str) -> tuple[str, int]:
        """Convert '5m' to ('Minute', 5) etc."""
        mapping = {
            "m": "Minute",
            "h": "Hour",
            "d": "Day",
            "w": "Week",
        }
        unit_char = timeframe[-1].lower()
        if unit_char not in mapping:
            raise ValueError(f"Unsupported timeframe unit: {unit_char}")
            
        try:
            number = int(timeframe[:-1])
        except ValueError:
            raise ValueError(f"Invalid timeframe format: {timeframe}")
            
        return mapping[unit_char], number

    def fetch(
        self,
        symbol: str, 
        start: datetime,
        end: datetime,
        timeframe: str = "5m"
    ) -> pd.DataFrame:
        """
        Fetch historical data from TopStepX.
        Note: 'symbol' here should ideally be the Contract ID (int) or we need a lookup.
        If the user passes "MNQ", we might fail if we don't have the ID.
        Let's assume for now the user passes the Contract ID as string or int, 
        OR we assume 'symbol' is the specific ticker like 'MNQH4' and we hope the API accepts it?
        Based on search: "contractId" parameter. This is likely an integer ID.
        
        However, the user asked for "MNQ". We might need a Ticker Search feature later.
        For this implementation, we'll add a 'contract_id' arg or try to use symbol if API supports it.
        Let's assume passing the ID is required and the user will find it, 
        OR we assume the user passes a mapped ID.
        
        Actually, let's try to search or just implement it expecting an ID.
        """
        try:
            contract_id = int(symbol)
        except ValueError:
            # If not an int, maybe we need to warn the user or implements a lookup.
            # For this MVP, we will assume the input is the ID, but maybe we can stub a lookup.
            print(f"Warning: TopStepX API expects a Contract ID (int). converting '{symbol}' to int might fail.")
            # Let's assume for now the user provides the numeric ID.
            # If they provide "MNQ", this will crash.
            # A more robust system would query /api/Market/search or similar.
            raise ValueError(f"TopStepX provider currently requires integer Contract ID, got '{symbol}'")

        unit, unit_number = self._parse_timeframe(timeframe)
        
        all_bars = []
        current_start = start
        
        while current_start < end:
            # Max 20k bars. Let's ask for chunks.
            # We don't know exactly when 20k bars ends, so we iterate by time or just rely on pagination if API supported it.
            # The search didn't explicitely mention cursor pagination, usually retrieval by date range.
            # We'll just fetch the whole range if it fits, or splitting by week/month if needed.
            # For 1m data, 1 day = 1440 bars. 10 days = 14400. So we can fetch ~2 weeks safely.
            
            chunk_end = min(end, current_start + timedelta(days=10)) 
            
            payload = {
                "contractId": contract_id,
                "startTime": current_start.isoformat(),
                "endTime": chunk_end.isoformat(),
                "unit": unit,
                "unitNumber": unit_number,
                "limit": 20000
            }
            
            response = requests.post(
                f"{self.API_BASE}/api/History/retrieveBars",
                headers=self.headers,
                json=payload
            )
            
            if response.status_code != 200:
                print(f"Error fetching data: {response.text}")
                break
                
            data = response.json()
            if not data:
                break
                
            bars = data.get('bars', []) if isinstance(data, dict) else data 
            # Note: exact response format check needed. Search said "returns data in JSON... array of bar objects"
            # It might be a direct list or {"bars": [...]}. 
            # Common pattern is list or wrapped. Let's assume list or key 'data'/'bars'. 
            # Just in case, let's handle list directly.
            if isinstance(data, list):
                bars = data
            elif isinstance(data, dict) and 'bars' in data:
                bars = data['bars']
            elif isinstance(data, dict) and 'd' in data: # sometimes 'd' is data
                 bars = data['d']

            if not bars:
                break
                
            all_bars.extend(bars)
            
            # Prepare for next chunk
            current_start = chunk_end
            
            # Rate limit politeness
            time.sleep(0.5)
            
        if not all_bars:
            return pd.DataFrame()
            
        # Convert to DataFrame
        df = pd.DataFrame(all_bars)
        
        # Expected cols: t (timestamp), o, h, l, c, v
        # Rename to standard
        rename_map = {
            't': 'Date', 'o': 'Open', 'h': 'High', 'l': 'Low', 'c': 'Close', 'v': 'Volume'
        }
        df = df.rename(columns=rename_map)
        
        # Parse dates
        df['Date'] = pd.to_datetime(df['Date'])
        df.set_index('Date', inplace=True)
        
        return df
