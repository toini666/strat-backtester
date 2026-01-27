"""
Topstep API client for fetching market data.

This module provides a client for interacting with the Topstep API
to fetch historical market data and contract information.
"""
import logging
import os
import time
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

# Request timeout in seconds
DEFAULT_TIMEOUT = 30
MAX_RETRIES = 3
RETRY_BACKOFF_FACTOR = 0.5


def create_session_with_retries() -> requests.Session:
    """
    Create a requests session with retry logic and exponential backoff.

    Returns:
        Configured requests Session with retry adapter.
    """
    session = requests.Session()

    retry_strategy = Retry(
        total=MAX_RETRIES,
        backoff_factor=RETRY_BACKOFF_FACTOR,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["HEAD", "GET", "POST", "PUT", "DELETE", "OPTIONS"]
    )

    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("https://", adapter)
    session.mount("http://", adapter)

    return session


class TopstepClient:
    """
    Client for interacting with the Topstep API.

    Handles authentication, token management, and data fetching
    with proper timeout and retry handling.

    Attributes:
        BASE_URL: The base URL for the Topstep API.
        username: The Topstep username from environment variables.
        api_key: The API key from environment variables.
        token: The current authentication token.
    """

    BASE_URL = "https://api.topstepx.com"

    def __init__(self, timeout: int = DEFAULT_TIMEOUT):
        """
        Initialize the Topstep client.

        Args:
            timeout: Request timeout in seconds (default: 30).
        """
        self.username = os.getenv("TOPSTEP_USERNAME") or os.getenv("TOPSTEPX_USERNAME")
        self.api_key = os.getenv("TOPSTEPX_TOKEN")
        self.token: Optional[str] = None
        self.token_expiry: Optional[datetime] = None
        self.timeout = timeout
        self._session = create_session_with_retries()

    def _authenticate(self) -> None:
        """
        Authenticate using UserName + ApiKey to get a Bearer Token.

        Raises:
            ValueError: If credentials are missing.
            ConnectionError: If authentication fails.
        """
        if not self.username or not self.api_key:
            raise ValueError("Missing TOPSTEP_USERNAME or TOPSTEPX_TOKEN in .env")

        url = f"{self.BASE_URL}/api/Auth/loginKey"
        payload = {
            "userName": self.username,
            "apiKey": self.api_key
        }

        logger.debug(f"Authenticating with Topstep API...")

        try:
            resp = self._session.post(
                url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=self.timeout
            )
        except requests.exceptions.Timeout:
            raise ConnectionError(f"Topstep authentication timed out after {self.timeout}s")
        except requests.exceptions.RequestException as e:
            raise ConnectionError(f"Topstep authentication request failed: {e}")

        if resp.status_code != 200:
            raise ConnectionError(f"Topstep Login Failed ({resp.status_code}): {resp.text}")

        data = resp.json()
        if not data.get("success"):
            raise ConnectionError(f"Topstep Login Error: {data.get('errorMessage')}")

        self.token = data.get("token")
        logger.info("Successfully authenticated with Topstep API")

    def _get_headers(self) -> Dict[str, str]:
        """
        Get headers for API requests, authenticating if necessary.

        Returns:
            Dictionary of HTTP headers including authorization.
        """
        if not self.token:
            self._authenticate()
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

    def _make_request(
        self,
        method: str,
        url: str,
        payload: Dict[str, Any],
        retry_on_auth_failure: bool = True
    ) -> Dict[str, Any]:
        """
        Make an API request with proper error handling and retry logic.

        Args:
            method: HTTP method (GET, POST, etc.).
            url: Full URL for the request.
            payload: JSON payload for the request.
            retry_on_auth_failure: Whether to retry once on authentication failure.

        Returns:
            Parsed JSON response.

        Raises:
            ConnectionError: If the request fails.
        """
        try:
            resp = self._session.request(
                method,
                url,
                headers=self._get_headers(),
                json=payload,
                timeout=self.timeout
            )
        except requests.exceptions.Timeout:
            raise ConnectionError(f"Request to {url} timed out after {self.timeout}s")
        except requests.exceptions.RequestException as e:
            raise ConnectionError(f"Request to {url} failed: {e}")

        # Handle authentication expiry
        if resp.status_code == 401 and retry_on_auth_failure:
            logger.warning("Token expired, re-authenticating...")
            self.token = None
            self._authenticate()
            return self._make_request(method, url, payload, retry_on_auth_failure=False)

        if resp.status_code != 200:
            raise ConnectionError(f"Request failed ({resp.status_code}): {resp.text}")

        return resp.json()

    def fetch_available_contracts(self) -> List[Dict[str, Any]]:
        """
        Fetch list of active contracts available for trading.

        Returns:
            List of contract dictionaries with id, name, tickSize, tickValue, etc.

        Raises:
            ConnectionError: If the request fails.
        """
        url = f"{self.BASE_URL}/api/Contract/available"
        payload = {"live": False}  # SIM/Combine contracts

        logger.debug("Fetching available contracts...")

        data = self._make_request("POST", url, payload)

        if not data.get("success"):
            raise ConnectionError(f"Contract fetch error: {data.get('errorMessage')}")

        contracts = data.get("contracts", [])
        logger.info(f"Fetched {len(contracts)} available contracts")
        return contracts

    def fetch_historical_data(
        self,
        contract_id: str,
        start: datetime,
        end: datetime,
        timeframe: str = '15m'
    ) -> pd.DataFrame:
        """
        Fetch historical OHLCV bars for a contract.

        Args:
            contract_id: The ID of the contract to fetch data for.
            start: Start datetime for the data range.
            end: End datetime for the data range.
            timeframe: Candle timeframe ('1m', '5m', '15m', '1h', '4h', '1d').

        Returns:
            DataFrame with columns: Open, High, Low, Close, Volume.
            Index is DatetimeIndex sorted in chronological order.

        Raises:
            ConnectionError: If the request fails.
        """
        url = f"{self.BASE_URL}/api/History/retrieveBars"

        # Map timeframe to Unit parameters
        # 1=Second, 2=Minute, 3=Hour, 4=Day
        unit = 2  # Minute default
        unit_number = 15

        timeframe_map = {
            '1m': (2, 1),
            '2m': (2, 2),
            '5m': (2, 5),
            '15m': (2, 15),
            '30m': (2, 30),
            '1h': (3, 1),
            '4h': (3, 4),
            '1d': (4, 1),
        }

        if timeframe in timeframe_map:
            unit, unit_number = timeframe_map[timeframe]
        else:
            logger.warning(f"Unknown timeframe '{timeframe}', defaulting to 15m")

        from datetime import timedelta
        
        all_bars = []
        current_start = start
        page_count = 0
        MAX_PAGES = 50 
        previous_last_bar_time = None
        
        while True:
            page_count += 1
            if page_count > MAX_PAGES:
                logger.warning(f"Hit maximum page limit ({MAX_PAGES}) for contract {contract_id}. Stopping fetch to prevent infinite loop.")
                break
                
            payload = {
                "contractId": contract_id,
                "live": False,
                "startTime": current_start.isoformat(),
                "endTime": end.isoformat(),
                "unit": unit,
                "unitNumber": unit_number,
                "limit": 10000,
                "includePartialBar": False
            }

            logger.debug(f"Fetching page {page_count} for {contract_id}, start={current_start}")

            try:
                data = self._make_request("POST", url, payload)
            except ConnectionError as e:
                logger.error(f"Error fetching data batch: {e}")
                if all_bars:
                    logger.warning("Returning partial data due to error")
                    break
                raise

            if not data.get("success"):
                if all_bars:
                    logger.warning(f"History fetch error on pagination: {data.get('errorMessage')}")
                    break
                raise ConnectionError(f"History fetch error: {data.get('errorMessage')}")

            bars = data.get("bars", [])
            
            if not bars:
                break
                
            all_bars.extend(bars)
            
            if len(bars) < 10000:
                break
            
            # Use the maximum time in the batch to ensure we advance
            # (defensive against unsorted data)
            batch_times = [pd.to_datetime(b['t']) for b in bars]
            last_bar_time = max(batch_times)
            
            # check if we are stuck (API returning same data range repeatedly)
            if previous_last_bar_time is not None and last_bar_time <= previous_last_bar_time:
                 logger.warning(f"Pagination stuck at {last_bar_time}. Forcing advance.")
                 # Force advance by a larger step (contract dependent, but 1m is safe for backfilling)
                 # If we are stuck, it means 'last_bar_time + 1s' resulted in same 'last_bar_time'.
                 # So we likely need to jump over the current bar.
                 current_start = last_bar_time + timedelta(minutes=1)
            else:
                 # Standard advance
                 current_start = last_bar_time + timedelta(seconds=1)

            previous_last_bar_time = last_bar_time

            # specific check if we reached the end time (or very close to it)
            # Handle timezone mismatch
            # Ensure we are working with pandas Timestamps for consistent comparison
            normalized_end = pd.Timestamp(end)
            if last_bar_time.tzinfo is not None and normalized_end.tzinfo is None:
                if last_bar_time.tzinfo == timezone.utc:
                     normalized_end = normalized_end.tz_localize('UTC')
                else:
                     last_bar_time = last_bar_time.tz_localize(None)
            elif last_bar_time.tzinfo is None and normalized_end.tzinfo is not None:
                last_bar_time = last_bar_time.tz_localize(normalized_end.tzinfo)
                
            if last_bar_time >= normalized_end:
                break

            # Update start time for next batch
            # current_start is already updated above

            # Respect rate limit (50 req / 30s = ~0.6s per req)
            # using 0.7s to be safe
            time.sleep(0.7)

        if not all_bars:
            logger.warning(f"No bars returned for contract {contract_id}")
            return pd.DataFrame(columns=['Open', 'High', 'Low', 'Close', 'Volume'])

        df = pd.DataFrame(all_bars)

        # Parse 't' as datetime and set index
        df['Date'] = pd.to_datetime(df['t'])
        
        # Remove duplicates that might occur from page boundaries
        df.drop_duplicates(subset=['Date'], keep='first', inplace=True)
        
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
        
        # Filter to ensure we stay within requested range (handling any boundary overlaps)
        # Normalize start/end timezone to match dataframe index
        df_start = pd.Timestamp(start)
        df_end = pd.Timestamp(end)
        
        if df.index.tz is not None:
             if df_start.tzinfo is None:
                 df_start = df_start.tz_localize('UTC')
             else:
                 df_start = df_start.tz_convert(df.index.tz)
                 
             if df_end.tzinfo is None:
                 df_end = df_end.tz_localize('UTC')
             else:
                 df_end = df_end.tz_convert(df.index.tz)
        else:
             # If index is naive, ensure start/end are naive
             if df_start.tzinfo is not None:
                 df_start = df_start.tz_localize(None)
             if df_end.tzinfo is not None:
                 df_end = df_end.tz_localize(None)
                 
        df = df[(df.index >= df_start) & (df.index <= df_end)]

        logger.info(f"Fetched {len(df)} bars for contract {contract_id} in total")

        return df[['Open', 'High', 'Low', 'Close', 'Volume']]
