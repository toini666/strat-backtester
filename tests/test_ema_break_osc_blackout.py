import numpy as np
import pandas as pd

import src.strategies.ema_break_osc as strategy_module
from src.strategies.ema_break_osc import EMABreakOsc


def test_ema_break_setup_survives_blackout_until_entry_bar(monkeypatch):
    strategy = EMABreakOsc()

    index = pd.date_range("2024-01-01 09:00:00+01:00", periods=12, freq="7min")
    data = pd.DataFrame(
        {
            "Open": [100.0] * 12,
            "High": [101.5] * 12,
            "Low": [99.5] * 12,
            "Close": [101.0] * 12,
            "Volume": [1000] * 12,
            "is_blackout": [False] * 12,
        },
        index=index,
    )

    break_idx = 8
    blackout_entry_idx = 9
    valid_entry_idx = 10

    data.iloc[break_idx, data.columns.get_loc("Open")] = 99.0
    data.iloc[break_idx, data.columns.get_loc("Close")] = 101.0
    data.iloc[break_idx, data.columns.get_loc("Low")] = 98.5
    data.iloc[blackout_entry_idx, data.columns.get_loc("is_blackout")] = True

    monkeypatch.setattr(
        strategy_module.ta,
        "ema",
        lambda series, length: pd.Series(np.full(len(series), 100.0), index=series.index),
    )
    monkeypatch.setattr(
        strategy,
        "_compute_oscillator",
        lambda close, high, low, hl2, mL, sT, sL: (
            pd.Series([0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1], index=close.index),
            pd.Series([0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], index=close.index),
        ),
    )
    monkeypatch.setattr(
        strategy,
        "_compute_mfi",
        lambda hl2, volume, mfL, mfS: pd.Series(np.zeros(len(hl2)), index=hl2.index),
    )
    monkeypatch.setattr(
        strategy,
        "_compute_mfi_cloud",
        lambda mfi_vals, mfL: (
            np.array([False] * break_idx + [False, True, True, True]),
            np.zeros(len(mfi_vals), dtype=bool),
            np.zeros(len(mfi_vals)),
            np.zeros(len(mfi_vals)),
        ),
    )

    signals = strategy.generate_signals(
        data,
        {
            "ema_length": 2,
            "ema2_length": 2,
            "hyper_wave_length": 2,
            "signal_length": 1,
            "mf_length": 2,
            "mf_smooth": 1,
            "break_wait_bars": 2,
            "hw_filter_on": False,
            "hw_extreme_filter_on": False,
            "max_candle_pct": 5.0,
            "require_ema_alignment": False,
            "tick_buffer": 1,
            "rr_partial": 2.0,
            "tp_points": 20.0,
            "tick_size": 0.25,
        },
    )

    debug_frame = signals["debug_frame"]
    long_entries = signals["long_entries"]

    assert bool(long_entries.iloc[blackout_entry_idx]) is False
    assert debug_frame["bars_since_long_break"].iloc[blackout_entry_idx] <= 2
    assert bool(long_entries.iloc[valid_entry_idx]) is True
