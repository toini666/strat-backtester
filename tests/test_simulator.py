import math

import pandas as pd

from src.engine.simulator import BlackoutWindow, SimulatorConfig, simulate


def _series(values, index):
    return pd.Series(values, index=index)


def test_simulator_blocks_entry_when_bar_close_is_in_blackout():
    index = pd.DatetimeIndex(
        [
            "2024-01-01 10:53:00+01:00",
            "2024-01-01 11:00:00+01:00",
        ]
    )
    data = pd.DataFrame(
        {
            "Open": [100.0, 100.5],
            "High": [101.0, 101.0],
            "Low": [99.5, 100.0],
            "Close": [100.5, 100.75],
            "Volume": [1000, 1000],
        },
        index=index,
    )

    signals = {
        "long_entries": _series([True, False], index),
        "short_entries": _series([False, False], index),
        "sl_long": _series([99.0, math.nan], index),
        "sl_short": _series([math.nan, math.nan], index),
        "tp1_long": _series([102.0, math.nan], index),
        "tp1_short": _series([math.nan, math.nan], index),
        "ema_main": _series([99.0, 99.0], index),
        "ema_secondary": _series([99.5, 99.5], index),
    }

    result = simulate(
        data=data,
        data_1m=pd.DataFrame(columns=data.columns),
        signals=signals,
        config=SimulatorConfig(
            initial_equity=10000.0,
            risk_per_trade=0.01,
            max_contracts=10,
            blackout_windows=[
                BlackoutWindow(
                    active=True,
                    start_hour=11,
                    start_minute=0,
                    end_hour=13,
                    end_minute=0,
                )
            ],
        ),
        ema_main=signals["ema_main"],
        ema_secondary=signals["ema_secondary"],
    )

    assert result["trades"] == []
    assert result["metrics"]["total_trades"] == 0


def test_simulator_uses_1m_sequence_for_tp1_touch_then_breakeven_before_partial_close():
    index = pd.DatetimeIndex(
        [
            "2024-01-01 09:00:00+01:00",
            "2024-01-01 09:07:00+01:00",
            "2024-01-01 09:14:00+01:00",
            "2024-01-01 09:21:00+01:00",
        ]
    )
    data = pd.DataFrame(
        {
            "Open": [100.0, 100.0, 101.0, 101.0],
            "High": [100.5, 101.5, 103.0, 101.0],
            "Low": [99.5, 99.75, 99.0, 100.5],
            "Close": [100.0, 101.0, 101.0, 101.0],
            "Volume": [1000, 1000, 1000, 1000],
        },
        index=index,
    )
    data_1m = pd.DataFrame(
        {
            "Open": [101.0, 101.2, 102.0, 101.0, 101.0, 101.0, 101.0],
            "High": [101.5, 102.2, 102.1, 101.0, 101.0, 101.0, 101.0],
            "Low": [100.8, 101.1, 100.9, 101.0, 101.0, 101.0, 101.0],
            "Close": [101.2, 102.0, 101.0, 101.0, 101.0, 101.0, 101.0],
            "Volume": [100, 100, 100, 100, 100, 100, 100],
        },
        index=pd.DatetimeIndex(
            [
                "2024-01-01 09:14:00+01:00",
                "2024-01-01 09:15:00+01:00",
                "2024-01-01 09:16:00+01:00",
                "2024-01-01 09:17:00+01:00",
                "2024-01-01 09:18:00+01:00",
                "2024-01-01 09:19:00+01:00",
                "2024-01-01 09:20:00+01:00",
            ]
        ),
    )

    signals = {
        "long_entries": _series([False, True, False, False], index),
        "short_entries": _series([False, False, False, False], index),
        "sl_long": _series([math.nan, 99.0, math.nan, math.nan], index),
        "sl_short": _series([math.nan, math.nan, math.nan, math.nan], index),
        "tp1_long": _series([math.nan, 102.0, math.nan, math.nan], index),
        "tp1_short": _series([math.nan, math.nan, math.nan, math.nan], index),
        "ema_main": _series([100.0, 100.0, 100.0, 100.0], index),
        "ema_secondary": _series([100.0, 100.0, 100.0, 100.0], index),
    }

    result = simulate(
        data=data,
        data_1m=data_1m,
        signals=signals,
        config=SimulatorConfig(
            initial_equity=10000.0,
            risk_per_trade=0.01,
            max_contracts=25,
            tick_size=0.25,
            tick_value=0.5,
            point_value=2.0,
            fee_per_trade=0.0,
            tp1_execution_mode="bar_close_if_touched",
        ),
        ema_main=signals["ema_main"],
        ema_secondary=signals["ema_secondary"],
    )

    assert result["metrics"]["total_trades"] == 1
    trade = result["trades"][0]
    assert trade["status"] == "Breakeven"
    assert trade["entry_time"] == "2024-01-01 09:07:00+01:00"
    assert trade["entry_execution_time"] == "2024-01-01 09:14:00+01:00"
    assert trade["exit_time"] == "2024-01-01 09:14:00+01:00"
    assert trade["exit_execution_time"] == "2024-01-01 09:17:00+01:00"
    assert [leg["status"] for leg in trade["legs"]] == ["Breakeven"]
    assert trade["exit_price"] == trade["entry_price"] == 101.0


def test_simulator_supports_close_based_hyperwave_partial_and_breakeven():
    index = pd.DatetimeIndex(
        [
            "2024-01-01 09:00:00+01:00",
            "2024-01-01 09:05:00+01:00",
            "2024-01-01 09:10:00+01:00",
        ]
    )
    data = pd.DataFrame(
        {
            "Open": [100.0, 101.0, 101.0],
            "High": [100.5, 102.5, 101.5],
            "Low": [99.5, 101.0, 99.75],
            "Close": [100.0, 102.0, 100.0],
            "Volume": [1000, 1000, 1000],
        },
        index=index,
    )
    signals = {
        "long_entries": _series([True, False, False], index),
        "short_entries": _series([False, False, False], index),
        "sl_long": _series([98.0, math.nan, math.nan], index),
        "sl_short": _series([math.nan, math.nan, math.nan], index),
        "tp1_long": _series([math.nan, math.nan, math.nan], index),
        "tp1_short": _series([math.nan, math.nan, math.nan], index),
        "disable_price_tp1": True,
        "partial_close_long": _series([False, True, False], index),
        "partial_close_short": _series([False, False, False], index),
        "canal_lower": _series([90.0, 90.0, 90.0], index),
        "canal_upper": _series([110.0, 110.0, 110.0], index),
        "canal_green": _series([False, False, False], index),
        "hma_flip_up": _series([False, False, False], index),
        "hma_flip_down": _series([False, False, False], index),
        "canal_exit_requires_arming": True,
        "ema_main": _series([0.0, 0.0, 0.0], index),
        "ema_secondary": _series([0.0, 0.0, 0.0], index),
    }

    result = simulate(
        data=data,
        data_1m=pd.DataFrame(columns=data.columns),
        signals=signals,
        config=SimulatorConfig(
            initial_equity=10000.0,
            risk_per_trade=0.01,
            max_contracts=10,
            tick_size=0.25,
            tick_value=0.5,
            point_value=2.0,
            fee_per_trade=0.0,
            tp1_partial_pct=0.25,
            auto_close_enabled=False,
            canal_exit_mode="break_hma",
        ),
        ema_main=signals["ema_main"],
        ema_secondary=signals["ema_secondary"],
    )

    trade = result["trades"][0]
    assert trade["status"] == "Breakeven"
    assert [leg["status"] for leg in trade["legs"]] == ["TP_HW", "Breakeven"]
    assert trade["legs"][0]["exit_price"] == 102.0
    assert trade["legs"][0]["size"] == 2.0
    assert trade["legs"][1]["exit_price"] == 100.0


def test_simulator_applies_min_rr_to_close_based_hyperwave_partial():
    index = pd.DatetimeIndex(
        [
            "2024-01-01 09:00:00+01:00",
            "2024-01-01 09:05:00+01:00",
            "2024-01-01 09:10:00+01:00",
        ]
    )
    data = pd.DataFrame(
        {
            "Open": [100.0, 100.0, 100.4],
            "High": [100.5, 100.6, 100.6],
            "Low": [99.5, 100.2, 100.2],
            "Close": [100.0, 100.4, 100.4],
            "Volume": [1000, 1000, 1000],
        },
        index=index,
    )
    signals = {
        "long_entries": _series([True, False, False], index),
        "short_entries": _series([False, False, False], index),
        "sl_long": _series([98.0, math.nan, math.nan], index),
        "sl_short": _series([math.nan, math.nan, math.nan], index),
        "tp1_long": _series([math.nan, math.nan, math.nan], index),
        "tp1_short": _series([math.nan, math.nan, math.nan], index),
        "disable_price_tp1": True,
        "partial_close_long": _series([False, True, False], index),
        "partial_close_short": _series([False, False, False], index),
        "canal_lower": _series([90.0, 90.0, 90.0], index),
        "canal_upper": _series([110.0, 110.0, 110.0], index),
        "canal_green": _series([False, False, False], index),
        "hma_flip_up": _series([False, False, False], index),
        "hma_flip_down": _series([False, False, False], index),
        "canal_exit_requires_arming": True,
        "ema_main": _series([0.0, 0.0, 0.0], index),
        "ema_secondary": _series([0.0, 0.0, 0.0], index),
    }

    blocked = simulate(
        data=data,
        data_1m=pd.DataFrame(columns=data.columns),
        signals=signals,
        config=SimulatorConfig(
            initial_equity=10000.0,
            risk_per_trade=0.01,
            max_contracts=10,
            tick_size=0.25,
            tick_value=0.5,
            point_value=2.0,
            fee_per_trade=0.0,
            tp1_partial_pct=0.25,
            tp2_partial_pct=0.0,
            auto_close_enabled=False,
            canal_exit_mode="break_hma",
            close_partial_min_rr=0.25,
        ),
        ema_main=signals["ema_main"],
        ema_secondary=signals["ema_secondary"],
    )
    allowed = simulate(
        data=data,
        data_1m=pd.DataFrame(columns=data.columns),
        signals=signals,
        config=SimulatorConfig(
            initial_equity=10000.0,
            risk_per_trade=0.01,
            max_contracts=10,
            tick_size=0.25,
            tick_value=0.5,
            point_value=2.0,
            fee_per_trade=0.0,
            tp1_partial_pct=0.25,
            tp2_partial_pct=0.0,
            auto_close_enabled=False,
            canal_exit_mode="break_hma",
            close_partial_min_rr=0.0,
        ),
        ema_main=signals["ema_main"],
        ema_secondary=signals["ema_secondary"],
    )

    assert [leg["status"] for leg in blocked["trades"][0]["legs"]] == ["End of Data"]
    assert [leg["status"] for leg in allowed["trades"][0]["legs"]] == ["TP_HW", "End of Data"]


def test_simulator_can_block_losing_hma_exit_before_close_based_partial():
    index = pd.DatetimeIndex(
        [
            "2024-01-01 09:00:00+01:00",
            "2024-01-01 09:05:00+01:00",
            "2024-01-01 09:10:00+01:00",
        ]
    )
    data = pd.DataFrame(
        {
            "Open": [106.0, 106.0, 94.0],
            "High": [107.0, 96.0, 95.0],
            "Low": [105.0, 93.0, 93.0],
            "Close": [106.0, 94.0, 94.0],
            "Volume": [1000, 1000, 1000],
        },
        index=index,
    )
    signals = {
        "long_entries": _series([True, False, False], index),
        "short_entries": _series([False, False, False], index),
        "sl_long": _series([90.0, math.nan, math.nan], index),
        "sl_short": _series([math.nan, math.nan, math.nan], index),
        "tp1_long": _series([math.nan, math.nan, math.nan], index),
        "tp1_short": _series([math.nan, math.nan, math.nan], index),
        "disable_price_tp1": True,
        "partial_close_long": _series([False, False, False], index),
        "partial_close_short": _series([False, False, False], index),
        "canal_lower": _series([95.0, 95.0, 95.0], index),
        "canal_upper": _series([105.0, 105.0, 105.0], index),
        "canal_green": _series([False, False, False], index),
        "hma_flip_up": _series([False, False, False], index),
        "hma_flip_down": _series([False, False, False], index),
        "canal_exit_requires_arming": True,
        "ema_main": _series([0.0, 0.0, 0.0], index),
        "ema_secondary": _series([0.0, 0.0, 0.0], index),
    }

    blocked = simulate(
        data=data,
        data_1m=pd.DataFrame(columns=data.columns),
        signals=signals,
        config=SimulatorConfig(
            initial_equity=10000.0,
            risk_per_trade=0.01,
            max_contracts=10,
            tick_size=0.25,
            tick_value=0.5,
            point_value=2.0,
            fee_per_trade=0.0,
            auto_close_enabled=False,
            canal_exit_mode="break_hma",
            block_loss_canal_exit_before_tp1=True,
        ),
        ema_main=signals["ema_main"],
        ema_secondary=signals["ema_secondary"],
    )
    unblocked = simulate(
        data=data,
        data_1m=pd.DataFrame(columns=data.columns),
        signals=signals,
        config=SimulatorConfig(
            initial_equity=10000.0,
            risk_per_trade=0.01,
            max_contracts=10,
            tick_size=0.25,
            tick_value=0.5,
            point_value=2.0,
            fee_per_trade=0.0,
            auto_close_enabled=False,
            canal_exit_mode="break_hma",
            block_loss_canal_exit_before_tp1=False,
        ),
        ema_main=signals["ema_main"],
        ema_secondary=signals["ema_secondary"],
    )

    assert blocked["trades"][0]["status"] == "End of Data"
    assert unblocked["trades"][0]["status"] == "Canal Exit"
    assert unblocked["trades"][0]["exit_time"] == "2024-01-01 09:05:00+01:00"


def test_simulator_hma_break_exit_waits_until_channel_is_armed():
    index = pd.DatetimeIndex(
        [
            "2024-01-01 09:00:00+01:00",
            "2024-01-01 09:05:00+01:00",
            "2024-01-01 09:10:00+01:00",
            "2024-01-01 09:15:00+01:00",
        ]
    )
    data = pd.DataFrame(
        {
            "Open": [100.0, 100.0, 94.0, 106.0],
            "High": [101.0, 95.0, 107.0, 95.0],
            "Low": [99.5, 93.0, 105.0, 93.0],
            "Close": [100.0, 94.0, 106.0, 94.0],
            "Volume": [1000, 1000, 1000, 1000],
        },
        index=index,
    )
    signals = {
        "long_entries": _series([True, False, False, False], index),
        "short_entries": _series([False, False, False, False], index),
        "sl_long": _series([90.0, math.nan, math.nan, math.nan], index),
        "sl_short": _series([math.nan, math.nan, math.nan, math.nan], index),
        "tp1_long": _series([math.nan, math.nan, math.nan, math.nan], index),
        "tp1_short": _series([math.nan, math.nan, math.nan, math.nan], index),
        "disable_price_tp1": True,
        "canal_lower": _series([95.0, 95.0, 95.0, 95.0], index),
        "canal_upper": _series([105.0, 105.0, 105.0, 105.0], index),
        "canal_green": _series([False, False, False, False], index),
        "hma_flip_up": _series([False, False, False, False], index),
        "hma_flip_down": _series([False, False, False, False], index),
        "canal_exit_requires_arming": True,
        "ema_main": _series([0.0, 0.0, 0.0, 0.0], index),
        "ema_secondary": _series([0.0, 0.0, 0.0, 0.0], index),
    }

    result = simulate(
        data=data,
        data_1m=pd.DataFrame(columns=data.columns),
        signals=signals,
        config=SimulatorConfig(
            initial_equity=10000.0,
            risk_per_trade=0.01,
            max_contracts=10,
            tick_size=0.25,
            tick_value=0.5,
            point_value=2.0,
            fee_per_trade=0.0,
            auto_close_enabled=False,
            canal_exit_mode="break_hma",
        ),
        ema_main=signals["ema_main"],
        ema_secondary=signals["ema_secondary"],
    )

    trade = result["trades"][0]
    assert trade["status"] == "Canal Exit"
    assert trade["exit_time"] == "2024-01-01 09:15:00+01:00"


def test_simulator_executes_tp1_at_timeframe_close_when_trade_survives_bar():
    index = pd.DatetimeIndex(
        [
            "2024-01-01 09:00:00+01:00",
            "2024-01-01 09:07:00+01:00",
            "2024-01-01 09:14:00+01:00",
            "2024-01-01 09:21:00+01:00",
        ]
    )
    data = pd.DataFrame(
        {
            "Open": [100.0, 100.0, 101.0, 102.25],
            "High": [100.5, 101.5, 102.5, 102.5],
            "Low": [99.5, 99.75, 100.75, 100.9],
            "Close": [100.0, 101.0, 102.25, 101.0],
            "Volume": [1000, 1000, 1000, 1000],
        },
        index=index,
    )
    data_1m = pd.DataFrame(
        {
            "Open": [101.0, 101.2, 101.8, 101.9, 102.0, 102.1, 102.2],
            "High": [101.5, 102.2, 102.3, 102.3, 102.4, 102.4, 102.5],
            "Low": [100.9, 101.6, 101.7, 101.8, 101.9, 102.0, 102.1],
            "Close": [101.2, 101.8, 101.9, 102.0, 102.1, 102.2, 102.25],
            "Volume": [100, 100, 100, 100, 100, 100, 100],
        },
        index=pd.DatetimeIndex(
            [
                "2024-01-01 09:14:00+01:00",
                "2024-01-01 09:15:00+01:00",
                "2024-01-01 09:16:00+01:00",
                "2024-01-01 09:17:00+01:00",
                "2024-01-01 09:18:00+01:00",
                "2024-01-01 09:19:00+01:00",
                "2024-01-01 09:20:00+01:00",
            ]
        ),
    )

    signals = {
        "long_entries": _series([False, True, False, False], index),
        "short_entries": _series([False, False, False, False], index),
        "sl_long": _series([math.nan, 99.0, math.nan, math.nan], index),
        "sl_short": _series([math.nan, math.nan, math.nan, math.nan], index),
        "tp1_long": _series([math.nan, 102.0, math.nan, math.nan], index),
        "tp1_short": _series([math.nan, math.nan, math.nan, math.nan], index),
        "ema_main": _series([100.0, 100.0, 100.0, 100.0], index),
        "ema_secondary": _series([100.0, 100.0, 100.0, 100.0], index),
    }

    result = simulate(
        data=data,
        data_1m=data_1m,
        signals=signals,
        config=SimulatorConfig(
            initial_equity=10000.0,
            risk_per_trade=0.01,
            max_contracts=25,
            tick_size=0.25,
            tick_value=0.5,
            point_value=2.0,
            fee_per_trade=0.0,
            tp1_execution_mode="bar_close_if_touched",
        ),
        ema_main=signals["ema_main"],
        ema_secondary=signals["ema_secondary"],
    )

    assert result["metrics"]["total_trades"] == 1
    trade = result["trades"][0]
    assert trade["status"] == "Breakeven"
    assert [leg["status"] for leg in trade["legs"]] == ["TP1", "Breakeven"]
    assert trade["legs"][0]["exit_time"] == "2024-01-01 09:14:00+01:00"
    assert trade["legs"][0]["exit_execution_time"] == "2024-01-01 09:21:00+01:00"
    assert trade["legs"][0]["exit_price"] == 102.25
    assert trade["legs"][1]["exit_time"] == "2024-01-01 09:21:00+01:00"
    assert trade["legs"][1]["exit_execution_time"] == "2024-01-01 09:28:00+01:00"


def test_simulator_can_execute_tp1_immediately_at_target_level():
    index = pd.DatetimeIndex(
        [
            "2024-01-01 09:00:00+01:00",
            "2024-01-01 09:07:00+01:00",
            "2024-01-01 09:14:00+01:00",
        ]
    )
    data = pd.DataFrame(
        {
            "Open": [100.0, 100.0, 101.0],
            "High": [100.5, 101.5, 102.5],
            "Low": [99.5, 99.75, 100.75],
            "Close": [100.0, 101.0, 101.25],
            "Volume": [1000, 1000, 1000],
        },
        index=index,
    )
    data_1m = pd.DataFrame(
        {
            "Open": [101.0, 101.2, 102.0, 101.8, 101.6, 101.4, 101.3],
            "High": [101.3, 101.8, 102.2, 101.9, 101.7, 101.5, 101.4],
            "Low": [100.9, 101.1, 101.9, 101.7, 101.5, 101.3, 101.2],
            "Close": [101.2, 101.7, 101.9, 101.8, 101.6, 101.4, 101.25],
            "Volume": [100, 100, 100, 100, 100, 100, 100],
        },
        index=pd.DatetimeIndex(
            [
                "2024-01-01 09:14:00+01:00",
                "2024-01-01 09:15:00+01:00",
                "2024-01-01 09:16:00+01:00",
                "2024-01-01 09:17:00+01:00",
                "2024-01-01 09:18:00+01:00",
                "2024-01-01 09:19:00+01:00",
                "2024-01-01 09:20:00+01:00",
            ]
        ),
    )

    signals = {
        "long_entries": _series([False, True, False], index),
        "short_entries": _series([False, False, False], index),
        "sl_long": _series([math.nan, 99.0, math.nan], index),
        "sl_short": _series([math.nan, math.nan, math.nan], index),
        "tp1_long": _series([math.nan, 102.0, math.nan], index),
        "tp1_short": _series([math.nan, math.nan, math.nan], index),
        "ema_main": _series([100.0, 100.0, 100.0], index),
        "ema_secondary": _series([100.0, 100.0, 100.0], index),
    }

    result = simulate(
        data=data,
        data_1m=data_1m,
        signals=signals,
        config=SimulatorConfig(
            initial_equity=10000.0,
            risk_per_trade=0.01,
            max_contracts=25,
            tick_size=0.25,
            tick_value=0.5,
            point_value=2.0,
            fee_per_trade=0.0,
            tp1_execution_mode="touch",
        ),
        ema_main=signals["ema_main"],
        ema_secondary=signals["ema_secondary"],
    )

    trade = result["trades"][0]
    assert [leg["status"] for leg in trade["legs"]] == ["TP1", "End of Data"]
    assert trade["legs"][0]["exit_execution_time"] == "2024-01-01 09:17:00+01:00"
    assert trade["legs"][0]["exit_price"] == 102.0


def test_simulator_partial_exit_sizes_use_initial_contracts():
    index = pd.DatetimeIndex(
        [
            "2024-01-01 09:00:00+01:00",
            "2024-01-01 09:07:00+01:00",
            "2024-01-01 09:14:00+01:00",
            "2024-01-01 09:21:00+01:00",
        ]
    )
    data = pd.DataFrame(
        {
            "Open": [100.0, 100.0, 102.0, 101.0],
            "High": [100.5, 102.5, 102.0, 101.5],
            "Low": [99.5, 100.0, 100.5, 100.5],
            "Close": [100.0, 102.0, 101.0, 101.0],
            "Volume": [1000, 1000, 1000, 1000],
        },
        index=index,
    )

    signals = {
        "long_entries": _series([True, False, False, False], index),
        "short_entries": _series([False, False, False, False], index),
        "sl_long": _series([99.0, math.nan, math.nan, math.nan], index),
        "sl_short": _series([math.nan, math.nan, math.nan, math.nan], index),
        "tp1_long": _series([102.0, math.nan, math.nan, math.nan], index),
        "tp1_short": _series([math.nan, math.nan, math.nan, math.nan], index),
        "ema_main": _series([99.0, 99.0, 99.0, 99.0], index),
        "ema_secondary": _series([100.0, 101.0, 101.5, 101.5], index),
    }

    result = simulate(
        data=data,
        data_1m=pd.DataFrame(columns=data.columns),
        signals=signals,
        config=SimulatorConfig(
            initial_equity=100.0,
            risk_per_trade=0.07,
            max_contracts=20,
            tick_size=1.0,
            tick_value=1.0,
            point_value=1.0,
            fee_per_trade=0.0,
            tp1_partial_pct=0.25,
            tp2_partial_pct=0.25,
        ),
        ema_main=signals["ema_main"],
        ema_secondary=signals["ema_secondary"],
    )

    trade = result["trades"][0]
    # 7 contracts: TP1 = floor(7*0.25)=1, TP2 = floor(7*0.25)=1, remaining = 5
    assert [leg["status"] for leg in trade["legs"]] == ["TP1", "TP2_EMA", "End of Data"]
    assert trade["size"] == 7.0
    assert trade["legs"][0]["size"] == 1
    assert trade["legs"][1]["size"] == 1
    assert trade["legs"][2]["size"] == 5.0


def test_simulator_ignores_partial_when_only_one_contract_remains():
    index = pd.DatetimeIndex(
        [
            "2024-01-01 09:00:00+01:00",
            "2024-01-01 09:07:00+01:00",
            "2024-01-01 09:14:00+01:00",
        ]
    )
    data = pd.DataFrame(
        {
            "Open": [100.0, 100.0, 102.0],
            "High": [100.5, 102.5, 102.0],
            "Low": [99.5, 100.0, 100.5],
            "Close": [100.0, 102.0, 101.0],
            "Volume": [1000, 1000, 1000],
        },
        index=index,
    )

    signals = {
        "long_entries": _series([True, False, False], index),
        "short_entries": _series([False, False, False], index),
        "sl_long": _series([99.0, math.nan, math.nan], index),
        "sl_short": _series([math.nan, math.nan, math.nan], index),
        "tp1_long": _series([102.0, math.nan, math.nan], index),
        "tp1_short": _series([math.nan, math.nan, math.nan], index),
        "ema_main": _series([99.0, 99.0, 99.0], index),
        "ema_secondary": _series([100.0, 101.0, 101.5], index),
    }

    result = simulate(
        data=data,
        data_1m=pd.DataFrame(columns=data.columns),
        signals=signals,
        config=SimulatorConfig(
            initial_equity=100.0,
            risk_per_trade=0.02,
            max_contracts=20,
            tick_size=1.0,
            tick_value=1.0,
            point_value=1.0,
            fee_per_trade=0.0,
        ),
        ema_main=signals["ema_main"],
        ema_secondary=signals["ema_secondary"],
    )

    trade = result["trades"][0]
    assert [leg["status"] for leg in trade["legs"]] == ["TP1", "End of Data"]
    assert trade["legs"][0]["size"] == 1
    assert trade["legs"][1]["size"] == 1.0


def test_simulator_activates_breakeven_on_tp1_touch_even_with_one_contract():
    index = pd.DatetimeIndex(
        [
            "2024-01-01 09:00:00+01:00",
            "2024-01-01 09:07:00+01:00",
            "2024-01-01 09:14:00+01:00",
        ]
    )
    data = pd.DataFrame(
        {
            "Open": [100.0, 100.0, 101.0],
            "High": [100.5, 101.5, 102.5],
            "Low": [99.5, 99.75, 100.75],
            "Close": [100.0, 101.0, 101.0],
            "Volume": [1000, 1000, 1000],
        },
        index=index,
    )
    data_1m = pd.DataFrame(
        {
            "Open": [101.0, 101.2, 102.0, 101.2, 101.0, 101.0, 101.0],
            "High": [101.4, 101.8, 102.2, 101.3, 101.1, 101.1, 101.1],
            "Low": [100.9, 101.1, 101.8, 101.0, 100.9, 100.9, 100.9],
            "Close": [101.2, 101.7, 101.9, 101.0, 101.0, 101.0, 101.0],
            "Volume": [100, 100, 100, 100, 100, 100, 100],
        },
        index=pd.DatetimeIndex(
            [
                "2024-01-01 09:14:00+01:00",
                "2024-01-01 09:15:00+01:00",
                "2024-01-01 09:16:00+01:00",
                "2024-01-01 09:17:00+01:00",
                "2024-01-01 09:18:00+01:00",
                "2024-01-01 09:19:00+01:00",
                "2024-01-01 09:20:00+01:00",
            ]
        ),
    )

    signals = {
        "long_entries": _series([False, True, False], index),
        "short_entries": _series([False, False, False], index),
        "sl_long": _series([math.nan, 99.0, math.nan], index),
        "sl_short": _series([math.nan, math.nan, math.nan], index),
        "tp1_long": _series([math.nan, 102.0, math.nan], index),
        "tp1_short": _series([math.nan, math.nan, math.nan], index),
        "ema_main": _series([100.0, 100.0, 100.0], index),
        "ema_secondary": _series([100.0, 100.0, 100.0], index),
    }

    result = simulate(
        data=data,
        data_1m=data_1m,
        signals=signals,
        config=SimulatorConfig(
            initial_equity=100.0,
            risk_per_trade=0.01,
            max_contracts=20,
            tick_size=1.0,
            tick_value=1.0,
            point_value=1.0,
            fee_per_trade=0.0,
            tp1_execution_mode="bar_close_if_touched",
        ),
        ema_main=signals["ema_main"],
        ema_secondary=signals["ema_secondary"],
    )

    trade = result["trades"][0]
    # With 1 contract, no partial exit happens, but TP1 touch still activates
    # breakeven.  The next bar's 1m data dips to entry (101.0 at 09:17),
    # so the position exits at breakeven.
    assert [leg["status"] for leg in trade["legs"]] == ["Breakeven"]


def test_simulator_auto_closes_at_exact_minute_with_1m_data():
    index = pd.DatetimeIndex(
        [
            "2024-01-01 20:46:00+01:00",
            "2024-01-01 20:53:00+01:00",
            "2024-01-01 21:00:00+01:00",
        ]
    )
    data = pd.DataFrame(
        {
            "Open": [100.0, 100.5, 101.0],
            "High": [100.8, 101.2, 101.2],
            "Low": [99.8, 100.2, 100.8],
            "Close": [100.5, 101.0, 101.0],
            "Volume": [1000, 1000, 1000],
        },
        index=index,
    )
    data_1m = pd.DataFrame(
        {
            "Open": [101.0, 101.1, 101.2, 101.3, 101.4, 101.4, 101.4],
            "High": [101.1, 101.2, 101.3, 101.4, 101.4, 101.4, 101.4],
            "Low": [100.9, 101.0, 101.1, 101.2, 101.3, 101.3, 101.3],
            "Close": [101.1, 101.2, 101.3, 101.4, 101.4, 101.4, 101.4],
            "Volume": [100, 100, 100, 100, 100, 100, 100],
        },
        index=pd.DatetimeIndex(
            [
                "2024-01-01 20:53:00+01:00",
                "2024-01-01 20:54:00+01:00",
                "2024-01-01 20:55:00+01:00",
                "2024-01-01 20:56:00+01:00",
                "2024-01-01 20:57:00+01:00",
                "2024-01-01 20:58:00+01:00",
                "2024-01-01 20:59:00+01:00",
            ]
        ),
    )

    signals = {
        "long_entries": _series([True, False, False], index),
        "short_entries": _series([False, False, False], index),
        "sl_long": _series([99.0, math.nan, math.nan], index),
        "sl_short": _series([math.nan, math.nan, math.nan], index),
        "tp1_long": _series([105.0, math.nan, math.nan], index),
        "tp1_short": _series([math.nan, math.nan, math.nan], index),
        "ema_main": _series([99.0, 99.0, 99.0], index),
        "ema_secondary": _series([99.0, 99.0, 99.0], index),
    }

    result = simulate(
        data=data,
        data_1m=data_1m,
        signals=signals,
        config=SimulatorConfig(
            initial_equity=10000.0,
            risk_per_trade=0.01,
            max_contracts=10,
            auto_close_hour=21,
            auto_close_minute=0,
            fee_per_trade=0.0,
        ),
        ema_main=signals["ema_main"],
        ema_secondary=signals["ema_secondary"],
    )

    assert result["metrics"]["total_trades"] == 1
    trade = result["trades"][0]
    assert trade["status"].startswith("Auto-Close")
    assert trade["entry_time"] == "2024-01-01 20:46:00+01:00"
    assert trade["entry_execution_time"] == "2024-01-01 20:53:00+01:00"
    assert trade["exit_time"] == "2024-01-01 20:53:00+01:00"
    assert trade["exit_execution_time"] == "2024-01-01 21:00:00+01:00"


def test_simulator_enforces_cooldown_in_engine():
    index = pd.DatetimeIndex(
        [
            "2024-01-01 09:00:00+01:00",
            "2024-01-01 09:07:00+01:00",
            "2024-01-01 09:14:00+01:00",
            "2024-01-01 09:21:00+01:00",
            "2024-01-01 09:28:00+01:00",
        ]
    )
    data = pd.DataFrame(
        {
            "Open": [100.0, 100.0, 100.5, 100.8, 101.0],
            "High": [100.2, 100.7, 101.0, 101.0, 101.3],
            "Low": [99.8, 99.6, 100.4, 100.7, 100.9],
            "Close": [100.0, 100.5, 100.8, 101.0, 101.2],
            "Volume": [1000, 1000, 1000, 1000, 1000],
        },
        index=index,
    )

    signals = {
        "long_entries": _series([True, False, True, False, False], index),
        "short_entries": _series([False, False, False, False, False], index),
        "sl_long": _series([99.0, math.nan, 99.75, 99.75, math.nan], index),
        "sl_short": _series([math.nan, math.nan, math.nan, math.nan, math.nan], index),
        "tp1_long": _series([105.0, math.nan, 105.0, 105.0, math.nan], index),
        "tp1_short": _series([math.nan, math.nan, math.nan, math.nan, math.nan], index),
        "ema_main": _series([101.0, 101.0, 101.0, 101.0, 99.0], index),
        "ema_secondary": _series([101.0, 101.0, 101.0, 101.0, 100.0], index),
    }

    result = simulate(
        data=data,
        data_1m=pd.DataFrame(columns=data.columns),
        signals=signals,
        config=SimulatorConfig(
            initial_equity=10000.0,
            risk_per_trade=0.01,
            max_contracts=10,
            tick_size=0.25,
            tick_value=0.5,
            point_value=2.0,
            fee_per_trade=0.0,
            cooldown_bars=2,
        ),
        ema_main=signals["ema_main"],
        ema_secondary=signals["ema_secondary"],
    )

    assert result["metrics"]["total_trades"] == 1
    trade = result["trades"][0]
    assert trade["status"] == "EMA Cross"
    assert trade["entry_time"] == "2024-01-01 09:00:00+01:00"


# ---------------------------------------------------------------------------
# Intra-bar daily limit mode
# ---------------------------------------------------------------------------

def _intra_bar_index():
    return pd.DatetimeIndex(
        [
            "2024-01-01 09:00:00+01:00",
            "2024-01-01 09:07:00+01:00",
        ]
    )


def test_simulator_intra_bar_daily_win_limit_force_closes_long_at_exact_trigger():
    """A long position is force-closed mid-bar when its floating PnL crosses
    the daily win limit, at the exact trigger price (not the bar's high or close).
    """
    index = _intra_bar_index()
    # Bar 1: entry at close=100. Bar 2: price ramps from 110 up to 350 then back.
    data = pd.DataFrame(
        {
            "Open": [100.0, 110.0],
            "High": [100.5, 350.0],
            "Low": [99.5, 110.0],
            "Close": [100.0, 200.0],
            "Volume": [1000, 1000],
        },
        index=index,
    )
    # 1m sub-bars for bar 2 (09:07 → 09:14, exclusive end). The third sub-bar
    # (09:09) is the first that contains the win trigger price (300) within its
    # [low, high] range.
    data_1m = pd.DataFrame(
        {
            "Open": [110.0, 120.0, 150.0, 305.0, 290.0, 270.0, 200.0],
            "High": [150.0, 200.0, 350.0, 320.0, 300.0, 280.0, 210.0],
            "Low":  [110.0, 115.0, 140.0, 280.0, 270.0, 260.0, 200.0],
            "Close":[120.0, 150.0, 300.0, 290.0, 270.0, 260.0, 200.0],
            "Volume":[100]*7,
        },
        index=pd.DatetimeIndex(
            [f"2024-01-01 09:{m:02d}:00+01:00" for m in range(7, 14)]
        ),
    )
    signals = {
        "long_entries": _series([True, False], index),
        "short_entries": _series([False, False], index),
        "sl_long": _series([99.0, math.nan], index),
        "sl_short": _series([math.nan, math.nan], index),
        # TP1 deliberately far away so it doesn't fire before the daily-limit check.
        "tp1_long": _series([1000.0, math.nan], index),
        "tp1_short": _series([math.nan, math.nan], index),
        # ema_main below close so EMA-cross exit can't fire either.
        "ema_main": _series([50.0, 50.0], index),
        "ema_secondary": _series([50.0, 50.0], index),
    }

    result = simulate(
        data=data,
        data_1m=data_1m,
        signals=signals,
        config=SimulatorConfig(
            initial_equity=100.0,
            risk_per_trade=0.01,
            max_contracts=10,
            tick_size=1.0,
            tick_value=1.0,
            point_value=1.0,
            fee_per_trade=0.0,
            auto_close_enabled=False,
            daily_win_limit_enabled=True,
            daily_win_limit=200.0,
            daily_limit_mode="intra_bar",
        ),
        ema_main=signals["ema_main"],
        ema_secondary=signals["ema_secondary"],
    )

    assert result["metrics"]["total_trades"] == 1
    trade = result["trades"][0]
    # Exit price is the win trigger (entry + win_limit / (R*pv) = 100 + 200/1 = 300),
    # NOT the bar's high (350) nor close (200).
    assert trade["exit_price"] == 300.0
    assert trade["status"] == "Daily Win Limit"
    assert trade["pnl"] == 200.0
    # The day should be flagged as a win-limit day.
    assert result["daily_limits_hit"].get("2024-01-01") == "win"


def test_simulator_intra_bar_daily_loss_limit_force_closes_long_before_sl():
    """A long position is force-closed at the loss-limit trigger price even
    though its hard SL has not been hit. The limit fires INSIDE the bar at the
    exact threshold price, not at the bar's low.
    """
    index = _intra_bar_index()
    data = pd.DataFrame(
        {
            "Open": [100.0, 100.0],
            "High": [100.5, 100.5],
            "Low":  [99.7, 98.7],   # Bar 2 low above SL (98) but below loss trigger (99.5).
            "Close":[100.0, 99.0],
            "Volume": [1000, 1000],
        },
        index=index,
    )
    data_1m = pd.DataFrame(
        {
            "Open": [100.0, 100.0, 99.9, 99.7, 99.5, 99.0, 99.0],
            "High": [100.5, 100.3, 100.0, 99.8, 99.6, 99.1, 99.0],
            "Low":  [99.9, 99.8, 99.7, 99.6, 98.7, 98.9, 99.0],
            "Close":[100.0, 99.9, 99.7, 99.6, 99.0, 99.0, 99.0],
            "Volume":[100]*7,
        },
        index=pd.DatetimeIndex(
            [f"2024-01-01 09:{m:02d}:00+01:00" for m in range(7, 14)]
        ),
    )
    signals = {
        "long_entries": _series([True, False], index),
        "short_entries": _series([False, False], index),
        "sl_long": _series([98.0, math.nan], index),
        "sl_short": _series([math.nan, math.nan], index),
        "tp1_long": _series([1000.0, math.nan], index),
        "tp1_short": _series([math.nan, math.nan], index),
        "ema_main": _series([50.0, 50.0], index),
        "ema_secondary": _series([50.0, 50.0], index),
    }

    # daily_loss_limit=0.5, R=1, pv=1 → loss trigger price = 100 - 0.5 = 99.5
    # The 5th 1m sub-bar (09:11) has L=98.7 < 99.5 < H=99.6 and O=99.5 → fires at 99.5.
    result = simulate(
        data=data,
        data_1m=data_1m,
        signals=signals,
        config=SimulatorConfig(
            initial_equity=100.0,
            risk_per_trade=0.01,
            max_contracts=10,
            tick_size=0.1,
            tick_value=0.1,
            point_value=1.0,
            fee_per_trade=0.0,
            auto_close_enabled=False,
            daily_loss_limit_enabled=True,
            daily_loss_limit=0.5,
            daily_limit_mode="intra_bar",
        ),
        ema_main=signals["ema_main"],
        ema_secondary=signals["ema_secondary"],
    )

    assert result["metrics"]["total_trades"] == 1
    trade = result["trades"][0]
    assert trade["status"] == "Daily Loss Limit"
    assert trade["exit_price"] == 99.5
    assert trade["pnl"] == -0.5
    assert result["daily_limits_hit"].get("2024-01-01") == "loss"


def test_simulator_after_close_mode_does_not_force_close_intrabar():
    """Same scenario as the intra-bar win test, but with the legacy
    after_close mode the position runs to end-of-data instead of being
    closed at the trigger price."""
    index = _intra_bar_index()
    data = pd.DataFrame(
        {
            "Open": [100.0, 110.0],
            "High": [100.5, 350.0],
            "Low": [99.5, 110.0],
            "Close": [100.0, 200.0],
            "Volume": [1000, 1000],
        },
        index=index,
    )
    data_1m = pd.DataFrame(
        {
            "Open": [110.0, 120.0, 150.0, 305.0, 290.0, 270.0, 200.0],
            "High": [150.0, 200.0, 350.0, 320.0, 300.0, 280.0, 210.0],
            "Low":  [110.0, 115.0, 140.0, 280.0, 270.0, 260.0, 200.0],
            "Close":[120.0, 150.0, 300.0, 290.0, 270.0, 260.0, 200.0],
            "Volume":[100]*7,
        },
        index=pd.DatetimeIndex(
            [f"2024-01-01 09:{m:02d}:00+01:00" for m in range(7, 14)]
        ),
    )
    signals = {
        "long_entries": _series([True, False], index),
        "short_entries": _series([False, False], index),
        "sl_long": _series([99.0, math.nan], index),
        "sl_short": _series([math.nan, math.nan], index),
        "tp1_long": _series([1000.0, math.nan], index),
        "tp1_short": _series([math.nan, math.nan], index),
        "ema_main": _series([50.0, 50.0], index),
        "ema_secondary": _series([50.0, 50.0], index),
    }

    result = simulate(
        data=data,
        data_1m=data_1m,
        signals=signals,
        config=SimulatorConfig(
            initial_equity=100.0,
            risk_per_trade=0.01,
            max_contracts=10,
            tick_size=1.0,
            tick_value=1.0,
            point_value=1.0,
            fee_per_trade=0.0,
            auto_close_enabled=False,
            daily_win_limit_enabled=True,
            daily_win_limit=200.0,
            daily_limit_mode="after_close",  # legacy mode
        ),
        ema_main=signals["ema_main"],
        ema_secondary=signals["ema_secondary"],
    )

    trade = result["trades"][0]
    # No intra-bar force-close: trade exits at end-of-data on bar 2's close (200).
    assert trade["status"] == "End of Data"
    assert trade["exit_price"] == 200.0
    # Realized PnL on close is only $100 — under the $200 win limit — so the
    # day is NOT flagged. (In intra_bar mode, the SAME data hits the trigger
    # at $300 mid-bar and flags the day; that contrast is the whole point.)
    assert trade["pnl"] == 100.0
    assert result["daily_limits_hit"] == {}
