"""
Tests for the FastAPI backend.
"""
import pytest
import sys
import os
import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from fastapi.testclient import TestClient
from pydantic import ValidationError

# Import after path setup
from backend.main import app
from backend.api import BacktestRequest, SIGNAL_CACHE, _annotate_blackout_flags, get_session
from src.engine.simulator import BlackoutWindow


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

    def test_blackout_annotation_uses_bar_close_time(self):
        index = pd.DatetimeIndex(
            [
                "2026-03-04 02:55:00+01:00",
                "2026-03-04 03:02:00+01:00",
                "2026-03-04 03:09:00+01:00",
            ]
        )
        data = pd.DataFrame(
            {
                "Open": [1.0, 1.0, 1.0],
                "High": [1.0, 1.0, 1.0],
                "Low": [1.0, 1.0, 1.0],
                "Close": [1.0, 1.0, 1.0],
                "Volume": [1, 1, 1],
            },
            index=index,
        )

        annotated = _annotate_blackout_flags(
            data,
            [
                BlackoutWindow(
                    active=True,
                    start_hour=1,
                    start_minute=0,
                    end_hour=3,
                    end_minute=0,
                )
            ],
        )

        assert bool(annotated.loc[pd.Timestamp("2026-03-04 02:55:00+01:00"), "is_blackout"]) is False


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


class TestResimulateEndpoint:
    def test_resimulate_rejects_blackout_change_for_blackout_sensitive_strategy(self, client):
        original_cache = SIGNAL_CACHE.copy()
        try:
            SIGNAL_CACHE.clear()
            SIGNAL_CACHE.update(
                {
                    "key": "test",
                    "sliced_data": [],
                    "sliced_signals": {},
                    "data_1m": [],
                    "specs": {"tick_size": 0.25, "tick_value": 0.5, "point_value": 2.0, "fee_per_trade": 0.0},
                    "simulator_settings": {},
                    "strategy_name": "UTBotAlligatorST",
                    "symbol": "MGC",
                    "params": {},
                    "blackout_signature": (
                        (False, 0, 0, 0, 5),
                        (False, 9, 0, 9, 5),
                        (True, 12, 0, 14, 0),
                        (False, 15, 30, 15, 35),
                        (True, 16, 30, 22, 0),
                        (True, 22, 0, 23, 59),
                    ),
                }
            )

            response = client.post(
                "/backtest/resimulate",
                json={
                    "initial_equity": 50000,
                    "risk_per_trade": 0.01,
                    "max_contracts": 10,
                    "engine_settings": {
                        "auto_close_enabled": True,
                        "auto_close_hour": 22,
                        "auto_close_minute": 0,
                        "blackout_windows": [
                            {"active": False, "start_hour": 0, "start_minute": 0, "end_hour": 0, "end_minute": 5},
                            {"active": False, "start_hour": 9, "start_minute": 0, "end_hour": 9, "end_minute": 5},
                            {"active": True, "start_hour": 12, "start_minute": 0, "end_hour": 13, "end_minute": 0},
                            {"active": False, "start_hour": 15, "start_minute": 30, "end_hour": 15, "end_minute": 35},
                            {"active": True, "start_hour": 16, "start_minute": 30, "end_hour": 22, "end_minute": 0},
                            {"active": True, "start_hour": 22, "start_minute": 0, "end_hour": 23, "end_minute": 59},
                        ],
                        "debug": False,
                        "daily_win_limit_enabled": False,
                        "daily_win_limit": 500,
                        "daily_loss_limit_enabled": False,
                        "daily_loss_limit": 700,
                    },
                },
            )

            assert response.status_code == 400
            assert "require a full backtest" in response.json()["detail"]
        finally:
            SIGNAL_CACHE.clear()
            SIGNAL_CACHE.update(original_cache)
