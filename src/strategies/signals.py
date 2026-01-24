"""
Standardized signal output format for trading strategies.

This module provides a dataclass for consistent signal output
across all trading strategies.
"""
from dataclasses import dataclass
from typing import Optional

import pandas as pd


@dataclass
class StrategySignals:
    """
    Standardized container for strategy signals.

    This dataclass ensures all strategies return signals in a consistent format,
    making it easier to process them in the backtesting engine.

    Attributes:
        long_entries: Boolean Series indicating long entry signals.
        long_exits: Boolean Series indicating long exit signals.
        short_entries: Boolean Series indicating short entry signals.
        short_exits: Boolean Series indicating short exit signals.
        execution_price: Optional Series of execution prices (uses Close if None).
        stop_loss_distance: Optional Series of stop loss distances per bar.
    """
    long_entries: pd.Series
    long_exits: pd.Series
    short_entries: pd.Series
    short_exits: pd.Series
    execution_price: Optional[pd.Series] = None
    stop_loss_distance: Optional[pd.Series] = None

    def __post_init__(self):
        """Validate that all required series have the same length."""
        lengths = [
            len(self.long_entries),
            len(self.long_exits),
            len(self.short_entries),
            len(self.short_exits)
        ]

        if len(set(lengths)) > 1:
            raise ValueError("All signal series must have the same length")

        if self.execution_price is not None and len(self.execution_price) != lengths[0]:
            raise ValueError("Execution price series must have the same length as signal series")

        if self.stop_loss_distance is not None and len(self.stop_loss_distance) != lengths[0]:
            raise ValueError("Stop loss distance series must have the same length as signal series")

    def to_tuple(self) -> tuple:
        """
        Convert to tuple format for backwards compatibility.

        Returns:
            Tuple of (long_entries, long_exits, short_entries, short_exits,
                     execution_price, stop_loss_distance) or shorter tuple if optional fields are None.
        """
        if self.execution_price is not None and self.stop_loss_distance is not None:
            return (
                self.long_entries,
                self.long_exits,
                self.short_entries,
                self.short_exits,
                self.execution_price,
                self.stop_loss_distance
            )
        elif self.execution_price is not None:
            return (
                self.long_entries,
                self.long_exits,
                self.short_entries,
                self.short_exits,
                self.execution_price
            )
        else:
            return (
                self.long_entries,
                self.long_exits,
                self.short_entries,
                self.short_exits
            )

    @classmethod
    def from_tuple(cls, signals: tuple, index: pd.Index) -> 'StrategySignals':
        """
        Create StrategySignals from a tuple (for backwards compatibility).

        Args:
            signals: Tuple of signal series.
            index: DataFrame index for creating empty series if needed.

        Returns:
            StrategySignals instance.
        """
        if len(signals) == 6:
            return cls(
                long_entries=signals[0],
                long_exits=signals[1],
                short_entries=signals[2],
                short_exits=signals[3],
                execution_price=signals[4],
                stop_loss_distance=signals[5]
            )
        elif len(signals) == 5:
            return cls(
                long_entries=signals[0],
                long_exits=signals[1],
                short_entries=signals[2],
                short_exits=signals[3],
                execution_price=signals[4]
            )
        elif len(signals) == 4:
            return cls(
                long_entries=signals[0],
                long_exits=signals[1],
                short_entries=signals[2],
                short_exits=signals[3]
            )
        elif len(signals) == 2:
            # Simple long-only or basic format
            return cls(
                long_entries=signals[0],
                long_exits=signals[1] if len(signals) > 1 else pd.Series(False, index=index),
                short_entries=pd.Series(False, index=index),
                short_exits=pd.Series(False, index=index)
            )
        else:
            raise ValueError(f"Unexpected signal tuple length: {len(signals)}")

    @property
    def has_entries(self) -> bool:
        """Check if there are any entry signals."""
        return self.long_entries.any() or self.short_entries.any()

    @property
    def total_signals(self) -> int:
        """Count total number of entry signals."""
        return int(self.long_entries.sum() + self.short_entries.sum())
