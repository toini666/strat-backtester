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

    @patch('requests.post')
    def test_get_headers_triggers_auth(self, mock_post):
        """Test that _get_headers triggers authentication if no token."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "success": True,
            "token": "test_token"
        }
        mock_post.return_value = mock_response

        with patch.dict(os.environ, {
            'TOPSTEP_USERNAME': 'test_user',
            'TOPSTEPX_TOKEN': 'test_key'
        }):
            client = TopstepClient()
            headers = client._get_headers()

            assert 'Authorization' in headers
            assert headers['Authorization'] == 'Bearer test_token'

    @patch('requests.post')
    def test_fetch_historical_data_returns_dataframe(self, mock_post):
        """Test that fetch_historical_data returns a properly formatted DataFrame."""
        # Mock auth response
        auth_response = MagicMock()
        auth_response.status_code = 200
        auth_response.json.return_value = {"success": True, "token": "test_token"}

        # Mock data response
        data_response = MagicMock()
        data_response.status_code = 200
        data_response.json.return_value = {
            "success": True,
            "bars": [
                {"t": "2024-01-01T10:00:00", "o": 100, "h": 105, "l": 98, "c": 103, "v": 1000},
                {"t": "2024-01-01T10:15:00", "o": 103, "h": 108, "l": 101, "c": 106, "v": 1100}
            ]
        }

        mock_post.side_effect = [auth_response, data_response]

        with patch.dict(os.environ, {
            'TOPSTEP_USERNAME': 'test_user',
            'TOPSTEPX_TOKEN': 'test_key'
        }):
            client = TopstepClient()
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

    @patch('requests.post')
    def test_fetch_available_contracts(self, mock_post):
        """Test fetching available contracts."""
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

        mock_post.side_effect = [auth_response, contracts_response]

        with patch.dict(os.environ, {
            'TOPSTEP_USERNAME': 'test_user',
            'TOPSTEPX_TOKEN': 'test_key'
        }):
            client = TopstepClient()
            contracts = client.fetch_available_contracts()

            assert isinstance(contracts, list)
            assert len(contracts) == 2
            assert contracts[0]["name"] == "MNQ"
