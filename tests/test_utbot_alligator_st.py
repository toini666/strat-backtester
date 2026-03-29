import numpy as np
import pandas as pd

import src.strategies.utbot_alligator_st as utbot_module
from src.strategies.utbot_alligator_st import UTBotAlligatorST


def test_utbot_retrace_entry_waits_until_blackout_ends(monkeypatch):
    strategy = UTBotAlligatorST()

    index = pd.date_range("2024-01-01 09:00:00+01:00", periods=14, freq="7min")
    data = pd.DataFrame(
        {
            "Open": [100.0] * 14,
            "High": [101.0] * 14,
            "Low": [99.0] * 14,
            "Close": [100.0] * 14,
            "Volume": [1000] * 14,
            "is_blackout": [False] * 14,
        },
        index=index,
    )

    signal_idx = 8
    blackout_touch_idx = 9
    valid_touch_idx = 11

    data.iloc[signal_idx, data.columns.get_loc("Low")] = 90.0
    data.iloc[signal_idx, data.columns.get_loc("High")] = 110.0
    data.iloc[10, data.columns.get_loc("Low")] = 101.0
    data.iloc[blackout_touch_idx, data.columns.get_loc("Low")] = 99.0
    data.iloc[valid_touch_idx, data.columns.get_loc("Low")] = 99.0
    data.iloc[blackout_touch_idx, data.columns.get_loc("is_blackout")] = True

    monkeypatch.setattr(
        utbot_module.ta,
        "atr",
        lambda high, low, close, length: pd.Series(np.ones(len(close)), index=close.index),
    )

    def fake_smma(values, length):
        mapping = {
            3: np.full(len(values), 80.0),
            2: np.full(len(values), 90.0),
            1: np.full(len(values), 100.0),
        }
        return mapping[length]

    ut_buy = np.zeros(len(data), dtype=bool)
    ut_buy[signal_idx] = True

    monkeypatch.setattr(strategy, "_smma", fake_smma)
    monkeypatch.setattr(
        strategy,
        "_compute_utbot",
        lambda src, atr, key_value: (
            np.zeros(len(src)),
            ut_buy,
            np.zeros(len(src), dtype=bool),
        ),
    )
    monkeypatch.setattr(
        strategy,
        "_compute_supertrend",
        lambda close, high, low, atr, multiplier: (
            np.full(len(close), 95.0),
            np.full(len(close), 105.0),
            np.ones(len(close), dtype=int),
            np.full(len(close), 95.0),
            np.zeros(len(close), dtype=bool),
            np.zeros(len(close), dtype=bool),
        ),
    )

    signals = strategy.generate_signals(
        data,
        {
            "tick_size": 0.25,
            "jaw_length": 3,
            "teeth_length": 2,
            "lips_length": 1,
            "jaw_offset": 0,
            "teeth_offset": 0,
            "lips_offset": 0,
            "ut_atr_period": 1,
            "st_atr_period": 1,
            "require_touch_alligator": False,
            "max_bars_retrace": 3,
        },
    )

    debug_frame = signals["debug_frame"]
    long_entries = signals["long_entries"]

    assert bool(long_entries.iloc[blackout_touch_idx]) is False
    assert debug_frame["trade_state"].iloc[blackout_touch_idx] == 3
    assert bool(long_entries.iloc[valid_touch_idx]) is True
    assert debug_frame["trade_state"].iloc[valid_touch_idx] == 5


def test_utbot_setup_can_form_during_blackout_and_enter_after(monkeypatch):
    strategy = UTBotAlligatorST()

    index = pd.date_range("2024-01-01 09:00:00+01:00", periods=14, freq="7min")
    data = pd.DataFrame(
        {
            "Open": [100.0] * 14,
            "High": [101.0] * 14,
            "Low": [99.0] * 14,
            "Close": [100.0] * 14,
            "Volume": [1000] * 14,
            "is_blackout": [False] * 14,
        },
        index=index,
    )

    signal_idx = 8
    valid_touch_idx = 10

    data.iloc[signal_idx, data.columns.get_loc("Low")] = 90.0
    data.iloc[signal_idx, data.columns.get_loc("High")] = 110.0
    data.iloc[9, data.columns.get_loc("Low")] = 101.0
    data.iloc[valid_touch_idx, data.columns.get_loc("Low")] = 99.0
    data.iloc[signal_idx, data.columns.get_loc("is_blackout")] = True

    monkeypatch.setattr(
        utbot_module.ta,
        "atr",
        lambda high, low, close, length: pd.Series(np.ones(len(close)), index=close.index),
    )

    def fake_smma(values, length):
        mapping = {
            3: np.full(len(values), 80.0),
            2: np.full(len(values), 90.0),
            1: np.full(len(values), 100.0),
        }
        return mapping[length]

    ut_buy = np.zeros(len(data), dtype=bool)
    ut_buy[signal_idx] = True

    monkeypatch.setattr(strategy, "_smma", fake_smma)
    monkeypatch.setattr(
        strategy,
        "_compute_utbot",
        lambda src, atr, key_value: (
            np.zeros(len(src)),
            ut_buy,
            np.zeros(len(src), dtype=bool),
        ),
    )
    monkeypatch.setattr(
        strategy,
        "_compute_supertrend",
        lambda close, high, low, atr, multiplier: (
            np.full(len(close), 95.0),
            np.full(len(close), 105.0),
            np.ones(len(close), dtype=int),
            np.full(len(close), 95.0),
            np.zeros(len(close), dtype=bool),
            np.zeros(len(close), dtype=bool),
        ),
    )

    signals = strategy.generate_signals(
        data,
        {
            "tick_size": 0.25,
            "jaw_length": 3,
            "teeth_length": 2,
            "lips_length": 1,
            "jaw_offset": 0,
            "teeth_offset": 0,
            "lips_offset": 0,
            "ut_atr_period": 1,
            "st_atr_period": 1,
            "require_touch_alligator": False,
            "max_bars_retrace": 3,
        },
    )

    debug_frame = signals["debug_frame"]
    long_entries = signals["long_entries"]

    assert debug_frame["trade_state"].iloc[signal_idx] == 3
    assert bool(long_entries.iloc[valid_touch_idx]) is True
    assert debug_frame["trade_state"].iloc[valid_touch_idx] == 5
