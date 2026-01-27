"""
Tests for data providers.
"""
import pytest
import pandas as pd
import sys
import os
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.data.base import DataProvider
from src.data.yfinance_provider import YFinanceProvider
from src.data.topstep import TopstepClient


class TestDataProviderBase:
    """Tests for the base DataProvider class."""

    def test_data_provider_is_abstract(self):
        """Test that DataProvider cannot be instantiated directly."""
        with pytest.raises(TypeError):
            DataProvider()


class TestYFinanceProvider:
    """Tests for the YFinance data provider."""

    def test_instantiation(self):
        """Test that YFinanceProvider can be instantiated."""
        provider = YFinanceProvider()
        assert provider is not None

    @patch('yfinance.download')
    def test_fetch_returns_dataframe(self, mock_download):
        """Test that fetch returns a DataFrame with correct columns."""
        # Mock yfinance response
        mock_df = pd.DataFrame({
            'Open': [100, 101, 102],
            'High': [105, 106, 107],
            'Low': [98, 99, 100],
            'Close': [103, 104, 105],
            'Volume': [1000, 1100, 1200]
        }, index=pd.date_range('2024-01-01', periods=3, freq='D'))

        mock_download.return_value = mock_df

        provider = YFinanceProvider()
        result = provider.fetch(
            symbol="AAPL",
            start=datetime(2024, 1, 1),
            end=datetime(2024, 1, 3),
            timeframe="1d"
        )

        assert isinstance(result, pd.DataFrame)
        assert 'Open' in result.columns
        assert 'High' in result.columns
        assert 'Low' in result.columns
        assert 'Close' in result.columns
        assert 'Volume' in result.columns

    @patch('yfinance.download')
    def test_fetch_handles_multi_index(self, mock_download):
        """Test that fetch handles MultiIndex columns correctly."""
        # Simulate MultiIndex columns (when downloading multiple tickers)
        arrays = [
            ['Open', 'High', 'Low', 'Close', 'Volume'],
            ['AAPL', 'AAPL', 'AAPL', 'AAPL', 'AAPL']
        ]
        tuples = list(zip(*arrays))
        index = pd.MultiIndex.from_tuples(tuples)

        mock_df = pd.DataFrame(
            [[100, 105, 98, 103, 1000]],
            columns=index,
            index=pd.date_range('2024-01-01', periods=1, freq='D')
        )

        mock_download.return_value = mock_df

        provider = YFinanceProvider()
        result = provider.fetch(
            symbol="AAPL",
            start=datetime(2024, 1, 1),
            end=datetime(2024, 1, 1),
            timeframe="1d"
        )

        # Should flatten MultiIndex
        assert not isinstance(result.columns, pd.MultiIndex)


class TestTopstepClient:
    """Tests for the Topstep data client."""

    def test_instantiation_without_credentials(self):
        """Test that TopstepClient can be instantiated even without credentials."""
        # Should not raise an error during instantiation
        with patch.dict(os.environ, {}, clear=True):
            client = TopstepClient()
            assert client is not None
            assert client.token is None

    def test_authenticate_raises_without_credentials(self):
        """Test that authentication fails without credentials."""
        with patch.dict(os.environ, {}, clear=True):
            client = TopstepClient()
            with pytest.raises(ValueError, match="Missing"):
                client._authenticate()

    def test_get_headers_triggers_auth(self):
        """Test that _get_headers triggers authentication if no token."""
        with patch.dict(os.environ, {
            'TOPSTEP_USERNAME': 'test_user',
            'TOPSTEPX_TOKEN': 'test_key'
        }):
            client = TopstepClient()
            
            # Mock the session
            client._session = MagicMock()
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "success": True,
                "token": "test_token"
            }
            client._session.post.return_value = mock_response
            
            headers = client._get_headers()

            assert 'Authorization' in headers
            assert headers['Authorization'] == 'Bearer test_token'
            client._session.post.assert_called_once()

    def test_fetch_historical_data_returns_dataframe(self):
        """Test that fetch_historical_data returns a properly formatted DataFrame."""
        with patch.dict(os.environ, {
            'TOPSTEP_USERNAME': 'test_user',
            'TOPSTEPX_TOKEN': 'test_key'
        }):
            client = TopstepClient()
            client._session = MagicMock()

            # Mock auth response
            auth_response = MagicMock()
            auth_response.status_code = 200
            auth_response.json.return_value = {"success": True, "token": "test_token"}

            # Mock data response
            # Note: _make_request uses session.request
            data_response = MagicMock()
            data_response.status_code = 200
            data_response.json.return_value = {
                "success": True,
                "bars": [
                    {"t": "2024-01-01T10:00:00", "o": 100, "h": 105, "l": 98, "c": 103, "v": 1000},
                    {"t": "2024-01-01T10:15:00", "o": 103, "h": 108, "l": 101, "c": 106, "v": 1100}
                ]
            }

            # First call is auth (post), second is data (request)
            # But _authenticate calls session.post specifically.
            # _make_request calls session.request.
            
            client._session.post.return_value = auth_response
            client._session.request.return_value = data_response

            result = client.fetch_historical_data(
                contract_id="123",
                start=datetime(2024, 1, 1),
                end=datetime(2024, 1, 2),
                timeframe="15m"
            )

            assert isinstance(result, pd.DataFrame)
            assert 'Open' in result.columns
            assert 'Close' in result.columns
            assert len(result) == 2

    def test_fetch_available_contracts(self):
        """Test fetching available contracts."""
        with patch.dict(os.environ, {
            'TOPSTEP_USERNAME': 'test_user',
            'TOPSTEPX_TOKEN': 'test_key'
        }):
            client = TopstepClient()
            client._session = MagicMock()

            auth_response = MagicMock()
            auth_response.status_code = 200
            auth_response.json.return_value = {"success": True, "token": "test_token"}

            contracts_response = MagicMock()
            contracts_response.status_code = 200
            contracts_response.json.return_value = {
                "success": True,
                "contracts": [
                    {"id": "1", "name": "MNQ", "tickSize": 0.25, "tickValue": 0.5},
                    {"id": "2", "name": "MES", "tickSize": 0.25, "tickValue": 1.25}
                ]
            }

            client._session.post.return_value = auth_response
            # _make_request uses session.request
            client._session.request.return_value = contracts_response

            contracts = client.fetch_available_contracts()

            assert isinstance(contracts, list)
            assert len(contracts) == 2
            assert contracts[0]["name"] == "MNQ"
            
    @patch('time.sleep')
    def test_fetch_historical_data_pagination(self, mock_sleep):
        """Test that fetch_historical_data handles backwards pagination correctly.

        The TopStep API returns the most recent bars first, so pagination
        works backwards from end to start.
        """
        with patch.dict(os.environ, {
            'TOPSTEP_USERNAME': 'test_user',
            'TOPSTEPX_TOKEN': 'test_key'
        }):
            client = TopstepClient()
            client._session = MagicMock()

            # Mock auth response
            auth_response = MagicMock()
            auth_response.status_code = 200
            auth_response.json.return_value = {"success": True, "token": "test_token"}
            client._session.post.return_value = auth_response

            # Mock data responses for 3 pages (backwards pagination)
            # API returns most recent bars first, so:
            # Page 1: bars 15000-24997 (most recent 10000)
            # Page 2: bars 5001-15000 (next 10000 going backwards)
            # Page 3: bars 0-5000 (remaining 5001 oldest bars)
            base_time = datetime(2024, 1, 1, 0, 0, 0)

            def create_bars(start_idx, end_idx):
                """Create bars for index range [start_idx, end_idx]"""
                return [{
                    "t": (base_time + timedelta(minutes=i)).isoformat(),
                    "o": 100+i, "h": 105+i, "l": 98+i, "c": 103+i, "v": 1000+i
                } for i in range(start_idx, end_idx + 1)]

            # Page 1: most recent 10000 bars (indices 14998-24997)
            page1_data = create_bars(14998, 24997)
            # Page 2: next 10000 bars going backwards (indices 4999-14998)
            # Note: 14998 overlaps with page 1
            page2_data = create_bars(4999, 14998)
            # Page 3: remaining bars (indices 0-4999)
            # Note: 4999 overlaps with page 2
            page3_data = create_bars(0, 4999)

            resp1 = MagicMock()
            resp1.status_code = 200
            resp1.json.return_value = {"success": True, "bars": page1_data}

            resp2 = MagicMock()
            resp2.status_code = 200
            resp2.json.return_value = {"success": True, "bars": page2_data}

            resp3 = MagicMock()
            resp3.status_code = 200
            resp3.json.return_value = {"success": True, "bars": page3_data}

            # _make_request uses session.request
            client._session.request.side_effect = [resp1, resp2, resp3]

            # Need to mock time.sleep to avoid waiting
            mock_sleep.return_value = None

            result = client.fetch_historical_data(
                contract_id="123",
                start=base_time,
                end=base_time + timedelta(minutes=30000),  # ample end time
                timeframe="1m"
            )

            # Total unique bars should be:
            # Page 1: 14998-24997 (10000 bars)
            # Page 2: 4999-14998 (10000 bars) -> 14998 is duplicate
            # Page 3: 0-4999 (5000 bars) -> 4999 is duplicate
            # Unique: 0 to 24997 => 24998 bars

            assert len(result) == 24998
            # Verify data is sorted chronologically (oldest first)
            assert result.index[0] < result.index[-1]
            # Verify sleep was called (for rate limiting between pages)
            assert mock_sleep.call_count == 2

