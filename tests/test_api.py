"""
Tests for the FastAPI backend.
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from fastapi.testclient import TestClient
from pydantic import ValidationError

# Import after path setup
from backend.main import app
from backend.api import BacktestRequest, get_session


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


class TestHealthEndpoints:
    """Tests for health check endpoints."""

    def test_root_endpoint(self, client):
        """Test the root endpoint returns correct status."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "online"
        assert "message" in data

    def test_health_endpoint(self, client):
        """Test the health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data


class TestStrategiesEndpoint:
    """Tests for the strategies endpoint."""

    def test_get_strategies(self, client):
        """Test getting list of available strategies."""
        response = client.get("/strategies")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_strategies_have_required_fields(self, client):
        """Test that each strategy has required fields."""
        response = client.get("/strategies")
        data = response.json()

        for strategy in data:
            assert "name" in strategy
            assert "description" in strategy
            assert "default_params" in strategy


class TestBacktestRequestValidation:
    """Tests for BacktestRequest validation."""

    def test_valid_request(self):
        """Test that a valid request passes validation."""
        request = BacktestRequest(
            strategy_name="RobReversal",
            ticker="BTC-USD",
            source="Yahoo",
            interval="15m",
            days=14,
            initial_equity=50000.0,
            risk_per_trade=0.01
        )
        assert request.strategy_name == "RobReversal"

    def test_invalid_source(self):
        """Test that invalid source raises validation error."""
        with pytest.raises(ValidationError):
            BacktestRequest(
                strategy_name="Test",
                ticker="BTC-USD",
                source="InvalidSource",  # Invalid
                interval="15m",
                days=14
            )

    def test_invalid_interval(self):
        """Test that invalid interval raises validation error."""
        with pytest.raises(ValidationError):
            BacktestRequest(
                strategy_name="Test",
                ticker="BTC-USD",
                source="Yahoo",
                interval="2m",  # Invalid - not in allowed values
                days=14
            )

    def test_days_out_of_range(self):
        """Test that days outside valid range raises error."""
        with pytest.raises(ValidationError):
            BacktestRequest(
                strategy_name="Test",
                ticker="BTC-USD",
                source="Yahoo",
                interval="15m",
                days=500  # > 365
            )

    def test_initial_equity_too_low(self):
        """Test that initial equity below minimum raises error."""
        with pytest.raises(ValidationError):
            BacktestRequest(
                strategy_name="Test",
                ticker="BTC-USD",
                source="Yahoo",
                interval="15m",
                days=14,
                initial_equity=100  # < 1000
            )

    def test_risk_per_trade_out_of_range(self):
        """Test that risk per trade outside range raises error."""
        with pytest.raises(ValidationError):
            BacktestRequest(
                strategy_name="Test",
                ticker="BTC-USD",
                source="Yahoo",
                interval="15m",
                days=14,
                risk_per_trade=0.5  # > 0.1 (10%)
            )

    def test_params_validation(self):
        """Test that extreme parameter values raise error."""
        with pytest.raises(ValidationError):
            BacktestRequest(
                strategy_name="Test",
                ticker="BTC-USD",
                source="Yahoo",
                interval="15m",
                days=14,
                params={"extreme_value": 999999}  # > 10000
            )


class TestSessionFunction:
    """Tests for the get_session utility function."""

    def test_asia_session(self):
        """Test Asia session detection (00:00 - 08:59)."""
        assert get_session("2024-01-15 03:30:00") == "Asia"
        assert get_session("2024-01-15 08:59:00") == "Asia"

    def test_uk_session(self):
        """Test UK session detection (09:00 - 15:29)."""
        assert get_session("2024-01-15 09:00:00") == "UK"
        assert get_session("2024-01-15 12:00:00") == "UK"
        assert get_session("2024-01-15 15:29:00") == "UK"

    def test_us_session(self):
        """Test US session detection (15:30 - 22:00)."""
        assert get_session("2024-01-15 15:30:00") == "US"
        assert get_session("2024-01-15 18:00:00") == "US"
        assert get_session("2024-01-15 22:00:00") == "US"

    def test_outside_session(self):
        """Test Outside session detection (22:01 - 23:59)."""
        assert get_session("2024-01-15 22:30:00") == "Outside"
        assert get_session("2024-01-15 23:59:00") == "Outside"

    def test_invalid_timestamp(self):
        """Test that invalid timestamp returns Unknown."""
        assert get_session("invalid") == "Unknown"
        assert get_session("") == "Unknown"


class TestBacktestEndpoint:
    """Tests for the backtest endpoint."""

    def test_backtest_invalid_strategy(self, client):
        """Test that requesting non-existent strategy returns 404."""
        response = client.post("/backtest", json={
            "strategy_name": "NonExistentStrategy",
            "ticker": "BTC-USD",
            "source": "Yahoo",
            "interval": "15m",
            "days": 7
        })
        assert response.status_code == 404

    def test_backtest_missing_required_fields(self, client):
        """Test that missing required fields return 422."""
        response = client.post("/backtest", json={
            "ticker": "BTC-USD"
            # Missing strategy_name
        })
        assert response.status_code == 422
