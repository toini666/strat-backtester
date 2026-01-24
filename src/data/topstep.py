import os
import requests
import pandas as pd
from datetime import datetime
from typing import Optional, Dict, Any, List

class TopstepClient:
    BASE_URL = "https://api.topstepx.com"
    
    def __init__(self):
        self.username = os.getenv("TOPSTEP_USERNAME") or os.getenv("TOPSTEPX_USERNAME")
        self.api_key = os.getenv("TOPSTEPX_TOKEN")
        self.token = None
        self.token_expiry = None

    def _authenticate(self):
        """Authenticates using UserName + ApiKey to get a Bearer Token."""
        if not self.username or not self.api_key:
            raise ValueError("Missing TOPSTEP_USERNAME or TOPSTEPX_TOKEN in .env")

        url = f"{self.BASE_URL}/api/Auth/loginKey"
        payload = {
            "userName": self.username,
            "apiKey": self.api_key
        }
        
        resp = requests.post(url, json=payload, headers={"Content-Type": "application/json"})
        if resp.status_code != 200:
            raise ConnectionError(f"Topstep Login Failed ({resp.status_code}): {resp.text}")
            
        data = resp.json()
        if not data.get("success"):
            raise ConnectionError(f"Topstep Login Error: {data.get('errorMessage')}")
            
        self.token = data.get("token")
        # In a real app, parse JWT to set expiry, or just re-auth on 401
        
    def _get_headers(self) -> Dict[str, str]:
        if not self.token:
            self._authenticate()
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

    def fetch_available_contracts(self) -> List[Dict[str, Any]]:
        """Fetches list of active contracts."""
        url = f"{self.BASE_URL}/api/Contract/available"
        # Use live=False to get SIM/Combine contracts which user likely has access to
        payload = {"live": False} 
        
        try:
            resp = requests.post(url, headers=self._get_headers(), json=payload)
        except ConnectionError:
            # Retry once if token expired
            self._authenticate()
            resp = requests.post(url, headers=self._get_headers(), json=payload)
            
        if resp.status_code != 200:
            raise ConnectionError(f"Failed to fetch contracts: {resp.text}")
            
        data = resp.json()
        if not data.get("success"):
             raise ConnectionError(f"Contract fetch error: {data.get('errorMessage')}")
             
        # Return full contract objects
        return data.get("contracts", [])

    def fetch_historical_data(self, contract_id: str, start: datetime, end: datetime, timeframe: str = '15m') -> pd.DataFrame:
        """
        Fetches historical bars. 
        Note: Topstep API might use different unit enums.
        """
        url = f"{self.BASE_URL}/api/History/retrieveBars"
        
        # Map timeframe to Unit parameters
        # 1=Second, 2=Minute, 3=Hour, 4=Day
        unit = 2 # Minute default
        unit_number = 15
        
        if timeframe == '1m': unit_number = 1
        elif timeframe == '5m': unit_number = 5
        elif timeframe == '15m': unit_number = 15
        elif timeframe == '1h': 
            unit = 3
            unit_number = 1
        elif timeframe == '4h': 
            unit = 3
            unit_number = 4
        elif timeframe == '1d': 
            unit = 4
            unit_number = 1
            
        payload = {
            "contractId": contract_id,
            "live": False, # Use Sim data
            "startTime": start.isoformat(),
            "endTime": end.isoformat(),
            "unit": unit,
            "unitNumber": unit_number,
            "limit": 10000,
            "includePartialBar": False
        }
        
        try:
            resp = requests.post(url, headers=self._get_headers(), json=payload)
        except ConnectionError:
            self._authenticate()
            resp = requests.post(url, headers=self._get_headers(), json=payload)

        if resp.status_code != 200:
             raise ConnectionError(f"Failed to fetch history: {resp.text}")
             
        data = resp.json()
        if not data.get("success"):
            raise ConnectionError(f"History fetch error: {data.get('errorMessage')}")
            
        bars = data.get("bars", [])
        if not bars:
            return pd.DataFrame()
            
        df = pd.DataFrame(bars)
        # Parse 't' as datetime and set index
        df['Date'] = pd.to_datetime(df['t'])
        df.set_index('Date', inplace=True)
        
        # Rename columns to standard OHLCV
        df.rename(columns={
            'o': 'Open',
            'h': 'High',
            'l': 'Low',
            'c': 'Close',
            'v': 'Volume'
        }, inplace=True)
        
        # Ensure chronological order (Oldest first)
        df.sort_index(ascending=True, inplace=True)
        
        return df[['Open', 'High', 'Low', 'Close', 'Volume']]
