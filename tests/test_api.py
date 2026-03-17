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

    def test_ema_break_strategy_exposes_only_strategy_specific_params(self, client):
        response = client.get("/strategies")
        data = response.json()
        ema_break = next((strategy for strategy in data if strategy["name"] == "EMABreakOsc"), None)

        if ema_break is None:
            pytest.skip("EMABreakOsc not loaded in this test environment")
        assert "auto_close_hour" not in ema_break["default_params"]
        assert "bo1_on" not in ema_break["default_params"]


class TestBacktestRequestValidation:
    """Tests for BacktestRequest validation."""

    def test_valid_request(self):
        """Test that a valid request passes validation."""
        request = BacktestRequest(
            strategy_name="EMABreakOsc",
            symbol="MNQ",
            interval="15m",
            start_datetime="2024-01-15T09:00",
            end_datetime="2024-01-15T16:00",
            initial_equity=50000.0,
            risk_per_trade=0.01
        )
        assert request.strategy_name == "EMABreakOsc"
        assert request.engine_settings.auto_close_enabled is True
        assert len(request.engine_settings.blackout_windows) == 6

    def test_invalid_symbol_too_short(self):
        """Test that invalid symbol raises validation error."""
        with pytest.raises(ValidationError):
            BacktestRequest(
                strategy_name="Test",
                symbol="",
                interval="15m",
                start_datetime="2024-01-15T09:00",
                end_datetime="2024-01-15T16:00",
            )

    def test_invalid_interval(self):
        """Test that invalid interval raises validation error."""
        with pytest.raises(ValidationError):
            BacktestRequest(
                strategy_name="Test",
                symbol="MNQ",
                interval="4m",
                start_datetime="2024-01-15T09:00",
                end_datetime="2024-01-15T16:00",
            )

    def test_missing_datetimes_raise_error(self):
        """Test that missing datetimes raise validation error."""
        with pytest.raises(ValidationError):
            BacktestRequest(
                strategy_name="Test",
                symbol="MNQ",
                interval="15m",
            )

    def test_initial_equity_too_low(self):
        """Test that initial equity below minimum raises error."""
        with pytest.raises(ValidationError):
            BacktestRequest(
                strategy_name="Test",
                symbol="MNQ",
                interval="15m",
                start_datetime="2024-01-15T09:00",
                end_datetime="2024-01-15T16:00",
                initial_equity=100  # < 1000
            )

    def test_risk_per_trade_out_of_range(self):
        """Test that risk per trade outside range raises error."""
        with pytest.raises(ValidationError):
            BacktestRequest(
                strategy_name="Test",
                symbol="MNQ",
                interval="15m",
                start_datetime="2024-01-15T09:00",
                end_datetime="2024-01-15T16:00",
                risk_per_trade=0.5  # > 0.1 (10%)
            )

    def test_params_validation(self):
        """Test that extreme parameter values raise error."""
        with pytest.raises(ValidationError):
            BacktestRequest(
                strategy_name="Test",
                symbol="MNQ",
                interval="15m",
                start_datetime="2024-01-15T09:00",
                end_datetime="2024-01-15T16:00",
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

    def test_late_hours_map_to_us(self):
        """Late hours (22:01+) now map to US instead of Outside."""
        assert get_session("2024-01-15 22:30:00") == "US"
        assert get_session("2024-01-15 23:59:00") == "US"

    def test_dst_shifted_sessions(self):
        """During US-DST / EU-standard misalignment, sessions shift -1h.

        2024-03-15 is after US DST (Mar 10) but before EU DST (Mar 31).
        Brussels-ET diff = 5h → offset = -1.
        Asia starts at 23:00, UK at 08:00, US at 14:30 (Brussels wall-clock).
        """
        # 23:00 Brussels → ref 00:00 → Asia
        assert get_session("2024-03-15 23:00:00") == "Asia"
        # 08:00 Brussels → ref 09:00 → UK
        assert get_session("2024-03-15 08:00:00") == "UK"
        # 14:30 Brussels → ref 15:30 → US
        assert get_session("2024-03-15 14:30:00") == "US"

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
            "symbol": "MNQ",
            "interval": "15m",
            "start_datetime": "2024-01-15T09:00",
            "end_datetime": "2024-01-15T16:00",
        })
        assert response.status_code == 404

    def test_backtest_missing_required_fields(self, client):
        """Test that missing required fields return 422."""
        response = client.post("/backtest", json={
            "symbol": "MNQ"
            # Missing strategy_name
        })
        assert response.status_code == 422
