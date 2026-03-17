"""
Tests for trading strategies.
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.strategies.base import Strategy


class TestStrategyBase:
    """Tests for the base Strategy class."""

    def test_strategy_is_abstract(self):
        """Test that Strategy cannot be instantiated directly."""
        with pytest.raises(TypeError):
            Strategy()

    def test_concrete_strategy_must_implement_generate_signals(self):
        """Test that subclasses must implement generate_signals."""
        class IncompleteStrategy(Strategy):
            pass

        with pytest.raises(TypeError):
            IncompleteStrategy()
