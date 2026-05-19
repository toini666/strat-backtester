"""Tests for the HMA-SSL-Osci v4 strategy.

Covers:
  * get_simulator_settings emits the v4 simulator keys.
  * Smoke test: generate_signals runs and emits the v4 signal surface.
  * V3-equivalence: V4 with V3-compatible flags reproduces V3 trades on the
    same synthetic data and config.
  * V4 RR-gated final exit defers when RR < threshold.
  * V4 move_to_be_on_fast_hma_cross moves SL to entry on the fast-HMA cross
    while in profit.
"""

import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.engine.simulator import SimulatorConfig, simulate
from src.strategies.hma_ssl_osci_v3 import HMASSLOsciV3
from src.strategies.hma_ssl_osci_v4 import HMASSLOsciV4, EARLY_EXIT_FIRED_MODES


def _base_params() -> dict:
    p = HMASSLOsciV4().default_params.copy()
    p.update(
        {
            "ema_len": 2,
            "hma1_len": 2,
            "hma2_len": 3,
            "hma_pol_bars": 99,
            "entry_window_bars": 5,
            "ssl_len": 3,
            "hyper_wave_length": 2,
            "signal_length": 2,
            "mf_length": 2,
            "mf_smooth": 2,
            "hw_dir_on": False,
            "hw_extreme_on": False,
            "sig_extreme_on": False,
            "hw_range_on": False,
            "cloud_on": False,
            "delta_on": False,
            "cloud_zero_on": False,
            "delta_ext_on": False,
            "max_candle_pct": 0.0,
            "max_sl_points": 500.0,
            "tick_buffer": 0,
            "tick_size": 0.25,
            "cooldown_bars": 0,
            "reject_entry_at_sl_extreme": False,
            "move_to_be_on_fast_hma_cross": False,
            "final_exit_min_rr": 0.0,
            "move_to_be_on_rejected_exit": False,
            "early_exit_fired_mode": "off",
        }
    )
    return p


def _build_data(length: int = 48) -> pd.DataFrame:
    index = pd.date_range(
        "2024-01-01", periods=length, freq="5min", tz="Europe/Brussels"
    )
    close = np.full(length, 100.0)
    return pd.DataFrame(
        {
            "Open": close,
            "High": close + 0.5,
            "Low": close - 0.5,
            "Close": close,
            "Volume": np.full(length, 1000.0),
        },
        index=index,
    )


def test_v4_simulator_settings_emit_v4_keys():
    settings = HMASSLOsciV4().get_simulator_settings(
        {
            "final_exit_min_rr": 1.5,
            "move_to_be_on_fast_hma_cross": True,
            "move_to_be_on_rejected_exit": True,
            "early_exit_fired_mode": "canal_inverse",
            "one_trade_per_entry_window": True,
        }
    )

    assert settings["canal_exit_mode"] == "v4_hw_rr"
    assert settings["tp1_partial_pct"] == 0.0
    assert settings["tp2_partial_pct"] == 0.0
    assert settings["one_trade_per_setup_window"] is True
    assert settings["final_exit_min_rr"] == 1.5
    assert settings["move_to_be_on_fast_hma_cross"] is True
    assert settings["move_to_be_on_rejected_exit"] is True
    assert settings["early_exit_fired_mode"] == "canal_inverse"


def test_v4_simulator_settings_reject_unknown_early_mode():
    import pytest

    with pytest.raises(ValueError):
        HMASSLOsciV4().get_simulator_settings({"early_exit_fired_mode": "BOGUS"})


def test_v4_default_params_mirror_v3_with_neutral_v4_keys():
    """V4 strategy defaults intentionally mirror V3 strategy defaults so
    V4-with-defaults reproduces V3-with-defaults out of the box. V4-new
    keys are set to neutral values (PineScript V4 defaults are
    documented but NOT used as Python defaults)."""
    p = HMASSLOsciV4().default_params

    # V3-aligned shared keys
    assert p["ema_len"] == 13
    assert p["hw_extreme_on"] is True
    assert p["sig_extreme_on"] is True
    assert p["sig_extreme"] == 35.0
    assert p["delta_on"] is True
    # V4-new keys at neutral / V3-compat values
    assert p["reject_entry_at_sl_extreme"] is False  # = V3 signal_candle_sl_on default
    assert p["move_to_be_on_fast_hma_cross"] is False
    assert p["final_exit_min_rr"] == 0.0
    assert p["move_to_be_on_rejected_exit"] is False
    assert p["early_exit_fired_mode"] == "off"


def test_v4_early_exit_modes_constant_matches_simulator():
    # Sanity check on the four supported modes (off, plus the three
    # PineScript options).
    assert set(EARLY_EXIT_FIRED_MODES) == {
        "off",
        "hw_rr",
        "canal_inverse",
        "next_slow_cross",
    }


def _install_fake_indicators(
    monkeypatch,
    strategy_cls,
    data: pd.DataFrame,
    *,
    hma1: pd.Series,
    hma2: pd.Series,
    bbmc: pd.Series,
    hw_cross_over_idx=None,
    hw_cross_under_idx=None,
):
    length = len(data)
    index = data.index
    src_ema = pd.Series(np.full(length, 100.0), index=index)
    canal_upper = pd.Series(np.maximum(hma1.values, hma2.values), index=index)
    canal_lower = pd.Series(np.minimum(hma1.values, hma2.values), index=index)
    canal_green = pd.Series(hma1.values > hma2.values, index=index)

    ssl_upper = pd.Series(bbmc.values + 1.0, index=index)
    ssl_lower = pd.Series(bbmc.values - 1.0, index=index)

    osc_sig = np.zeros(length)
    osc_sgd = np.zeros(length)
    if hw_cross_over_idx is not None:
        for k in hw_cross_over_idx:
            osc_sig[k - 1] = -1.0
            osc_sgd[k - 1] = 1.0
            osc_sig[k] = 1.0
            osc_sgd[k] = -1.0
    if hw_cross_under_idx is not None:
        for k in hw_cross_under_idx:
            osc_sig[k - 1] = 1.0
            osc_sgd[k - 1] = -1.0
            osc_sig[k] = -1.0
            osc_sgd[k] = 1.0
    osc_sig_s = pd.Series(osc_sig, index=index)
    osc_sgd_s = pd.Series(osc_sgd, index=index)

    mfi = pd.Series(np.zeros(length), index=index)
    cloud_long = np.zeros(length, dtype=bool)
    cloud_short = np.zeros(length, dtype=bool)
    cloud_ref = np.full(length, np.nan)
    cloud_line = np.full(length, np.nan)

    monkeypatch.setattr(
        strategy_cls,
        "_compute_hma_canal_full",
        staticmethod(
            lambda close, ema_len, hma1_len, hma2_len, amp_mult: (
                src_ema,
                hma1,
                hma2,
                canal_upper,
                canal_lower,
                canal_green,
            )
        ),
    )
    monkeypatch.setattr(
        strategy_cls,
        "_compute_ssl",
        staticmethod(
            lambda close, high, low, length, mult: (bbmc, ssl_upper, ssl_lower)
        ),
    )
    monkeypatch.setattr(
        strategy_cls,
        "_compute_oscillator",
        staticmethod(
            lambda close, high, low, hl2, mL, sT, sL: (osc_sig_s, osc_sgd_s)
        ),
    )
    monkeypatch.setattr(
        strategy_cls,
        "_compute_mfi",
        staticmethod(lambda hl2, volume, mfL, mfS: mfi),
    )
    monkeypatch.setattr(
        strategy_cls,
        "_compute_mfi_cloud",
        staticmethod(
            lambda mfi_values, mfL: (cloud_long, cloud_short, cloud_ref, cloud_line)
        ),
    )


def test_v4_signals_match_v3_when_sl_extreme_filter_off(monkeypatch):
    """With reject_entry_at_sl_extreme=False (V3 default), V4 and V3 produce
    identical entry / SL / fast-HMA-exit signals on the same synthetic data."""
    length = 48
    data = _build_data(length)

    hma1 = np.full(length, 102.0)
    hma2 = np.full(length, 101.5)
    bbmc = np.full(length, 100.0)
    hma2[30:] = 99.0
    hma1[34] = 99.5
    hma1[35:] = 101.0
    hw_low_idx = list(range(20, 30, 2))

    # V3 run
    _install_fake_indicators(
        monkeypatch,
        HMASSLOsciV3,
        data,
        hma1=pd.Series(hma1, index=data.index),
        hma2=pd.Series(hma2, index=data.index),
        bbmc=pd.Series(bbmc, index=data.index),
        hw_cross_over_idx=hw_low_idx,
    )
    v3_params = HMASSLOsciV3().default_params.copy()
    v3_params.update(
        {
            "ema_len": 2,
            "hma1_len": 2,
            "hma2_len": 3,
            "hma_pol_bars": 99,
            "entry_window_bars": 5,
            "ssl_len": 3,
            "hyper_wave_length": 2,
            "signal_length": 2,
            "mf_length": 2,
            "mf_smooth": 2,
            "hw_dir_on": False,
            "hw_extreme_on": False,
            "sig_extreme_on": False,
            "hw_range_on": False,
            "cloud_on": False,
            "delta_on": False,
            "cloud_zero_on": False,
            "delta_ext_on": False,
            "max_candle_pct": 0.0,
            "max_sl_points": 500.0,
            "tick_buffer": 0,
            "tick_size": 0.25,
            "cooldown_bars": 0,
            "signal_candle_sl_on": False,
            "hw_partial_pct": 0.0,
        }
    )
    v3_sigs = HMASSLOsciV3().generate_signals(data.copy(), v3_params)

    # V4 run with same indicators stub
    _install_fake_indicators(
        monkeypatch,
        HMASSLOsciV4,
        data,
        hma1=pd.Series(hma1, index=data.index),
        hma2=pd.Series(hma2, index=data.index),
        bbmc=pd.Series(bbmc, index=data.index),
        hw_cross_over_idx=hw_low_idx,
    )
    v4_sigs = HMASSLOsciV4().generate_signals(data.copy(), _base_params())

    # Compare entry signals + SLs + fast-HMA exit signals.
    pd.testing.assert_series_equal(
        v3_sigs["long_entries"],
        v4_sigs["long_entries"],
        check_names=False,
    )
    pd.testing.assert_series_equal(
        v3_sigs["short_entries"],
        v4_sigs["short_entries"],
        check_names=False,
    )
    pd.testing.assert_series_equal(
        v3_sigs["sl_long"], v4_sigs["sl_long"], check_names=False
    )
    pd.testing.assert_series_equal(
        v3_sigs["sl_short"], v4_sigs["sl_short"], check_names=False
    )
    pd.testing.assert_series_equal(
        v3_sigs["fast_hma_exit_long"],
        v4_sigs["fast_hma_exit_long"],
        check_names=False,
    )
    pd.testing.assert_series_equal(
        v3_sigs["fast_hma_exit_short"],
        v4_sigs["fast_hma_exit_short"],
        check_names=False,
    )
    # V4 also exposes hma1_above_ssl + slow crosses.
    assert "hma1_above_ssl" in v4_sigs
    assert "slow_cross_long" in v4_sigs
    assert "slow_cross_short" in v4_sigs


def _simulate_v4(df, signals, *, canal_lower=None, canal_upper=None, **cfg_kwargs):
    n = len(df)
    sigs = {
        "long_entries": pd.Series([False] * n, index=df.index),
        "short_entries": pd.Series([False] * n, index=df.index),
        "sl_long": pd.Series([np.nan] * n, index=df.index),
        "sl_short": pd.Series([np.nan] * n, index=df.index),
        "tp1_long": pd.Series([np.nan] * n, index=df.index),
        "tp1_short": pd.Series([np.nan] * n, index=df.index),
        "disable_price_tp1": True,
        "fast_hma_exit_long": pd.Series([False] * n, index=df.index),
        "fast_hma_exit_short": pd.Series([False] * n, index=df.index),
        "hw_cross_over": pd.Series([False] * n, index=df.index),
        "hw_cross_under": pd.Series([False] * n, index=df.index),
        "canal_lower": canal_lower
        if canal_lower is not None
        else pd.Series([0.0] * n, index=df.index),
        "canal_upper": canal_upper
        if canal_upper is not None
        else pd.Series([1e9] * n, index=df.index),
        "canal_green": pd.Series([False] * n, index=df.index),
        "setup_bar_long": pd.Series([-1] * n, index=df.index),
        "setup_bar_short": pd.Series([-1] * n, index=df.index),
        "hma1_above_ssl": pd.Series([False] * n, index=df.index),
        "slow_cross_long": pd.Series([False] * n, index=df.index),
        "slow_cross_short": pd.Series([False] * n, index=df.index),
        "ema_main": pd.Series([100.0] * n, index=df.index),
        "ema_secondary": pd.Series([100.0] * n, index=df.index),
    }
    sigs.update(signals)
    cfg = SimulatorConfig(
        initial_equity=50000,
        risk_per_trade=0.01,
        tick_size=0.25,
        tick_value=0.5,
        point_value=2.0,
        fee_per_trade=0.0,
        auto_close_enabled=False,
        blackout_windows=[],
        cooldown_bars=0,
        tp1_execution_mode="touch",
        tp1_partial_pct=0.0,
        tp2_partial_pct=0.0,
        canal_exit_mode="v4_hw_rr",
        **cfg_kwargs,
    )
    return simulate(df, df, sigs, cfg, sigs["ema_main"], sigs["ema_secondary"])


def test_v4_basic_final_exit_on_fast_hma_then_hw_cross():
    """A long enters in profit, fast-HMA exit fires + HW cross on the SAME bar
    → exit at close, no RR gating (final_exit_min_rr=0)."""
    length = 6
    index = pd.date_range(
        "2024-01-01", periods=length, freq="5min", tz="Europe/Brussels"
    )
    df = pd.DataFrame(
        {
            "Open": [100.0, 100.0, 101.0, 102.0, 103.0, 103.0],
            "High": [100.5, 100.5, 101.5, 102.5, 103.5, 103.5],
            "Low": [99.5, 99.5, 100.5, 101.5, 102.5, 102.5],
            "Close": [100.0, 100.0, 101.0, 102.0, 103.0, 103.0],
            "Volume": [1000] * length,
        },
        index=index,
    )

    signals = {
        "long_entries": pd.Series(
            [False, True, False, False, False, False], index=index
        ),
        "sl_long": pd.Series([np.nan, 95.0, 95.0, 95.0, 95.0, 95.0], index=index),
        "fast_hma_exit_long": pd.Series(
            [False, False, False, False, True, False], index=index
        ),
        "hw_cross_over": pd.Series(
            [False, False, False, False, True, False], index=index
        ),
    }
    result = _simulate_v4(df, signals)
    assert len(result["trades"]) == 1
    assert result["trades"][0]["status"] == "Canal Exit"


def test_v4_final_exit_deferred_when_rr_below_threshold():
    """Fast-HMA exit + HW cross fire while trade is barely in profit; with
    final_exit_min_rr=2.0 the exit is deferred (no trade closed yet)."""
    length = 6
    index = pd.date_range(
        "2024-01-01", periods=length, freq="5min", tz="Europe/Brussels"
    )
    # entry @ 100, SL @ 95 → risk 5 pts. close=101 → reward 1 pt → RR=0.2.
    df = pd.DataFrame(
        {
            "Open": [100.0, 100.0, 101.0, 101.0, 101.0, 101.0],
            "High": [100.5, 100.5, 101.5, 101.5, 101.5, 101.5],
            "Low": [99.5, 99.5, 100.5, 100.5, 100.5, 100.5],
            "Close": [100.0, 100.0, 101.0, 101.0, 101.0, 101.0],
            "Volume": [1000] * length,
        },
        index=index,
    )
    signals = {
        "long_entries": pd.Series(
            [False, True, False, False, False, False], index=index
        ),
        "sl_long": pd.Series([np.nan, 95.0, 95.0, 95.0, 95.0, 95.0], index=index),
        "fast_hma_exit_long": pd.Series(
            [False, False, False, True, False, False], index=index
        ),
        "hw_cross_over": pd.Series(
            [False, False, False, True, False, False], index=index
        ),
    }
    result = _simulate_v4(df, signals, final_exit_min_rr=2.0)
    # No exit yet (deferred); position closes at end of data.
    assert len(result["trades"]) == 1
    assert result["trades"][0]["status"] == "End of Data"


def test_v4_move_to_be_on_rejected_exit_moves_stop_when_in_profit():
    """RR gate rejects the exit; move_to_be_on_rejected_exit pulls SL to entry,
    so a later dip to entry closes as Stop Loss (label) at entry price."""
    length = 7
    index = pd.date_range(
        "2024-01-01", periods=length, freq="5min", tz="Europe/Brussels"
    )
    df = pd.DataFrame(
        {
            "Open": [100.0, 100.0, 101.0, 101.0, 100.0, 99.5, 99.0],
            "High": [100.5, 100.5, 101.5, 101.5, 100.5, 100.0, 99.5],
            "Low": [99.5, 99.5, 100.5, 100.5, 99.5, 99.0, 98.5],
            "Close": [100.0, 100.0, 101.0, 101.0, 100.0, 99.5, 99.0],
            "Volume": [1000] * length,
        },
        index=index,
    )
    signals = {
        "long_entries": pd.Series(
            [False, True, False, False, False, False, False], index=index
        ),
        "sl_long": pd.Series(
            [np.nan, 95.0, 95.0, 95.0, 95.0, 95.0, 95.0], index=index
        ),
        # Fast HMA cross + HW cross fire on bar 3, but RR=1/5=0.2 (close=101,
        # entry=100, risk=5) — far below threshold 2.0 → deferred.  With
        # move_to_be_on_rejected_exit=True the SL ratchets to entry=100.
        "fast_hma_exit_long": pd.Series(
            [False, False, False, True, False, False, False], index=index
        ),
        "hw_cross_over": pd.Series(
            [False, False, False, True, False, False, False], index=index
        ),
    }
    result = _simulate_v4(
        df,
        signals,
        final_exit_min_rr=2.0,
        move_to_be_on_rejected_exit=True,
    )
    assert len(result["trades"]) == 1
    trade = result["trades"][0]
    # Bar 4 low touches entry @ 100 → SL hit at entry → "Stop Loss" label
    # (move_to_be_on_rejected_exit does NOT set tp1_hit, so the label stays
    # Stop Loss even though the price equals entry).
    assert trade["status"] == "Stop Loss"
    assert trade["exit_price"] == 100.0


def test_v4_move_to_be_on_fast_hma_cross_sets_tp1_and_be_label():
    """fast_hma_exit fires WITHOUT a HW cross same bar → no exit triggered,
    but the optional BE-on-cross moves SL to entry and sets tp1_hit.  A later
    dip to entry closes as 'Breakeven'."""
    length = 7
    index = pd.date_range(
        "2024-01-01", periods=length, freq="5min", tz="Europe/Brussels"
    )
    df = pd.DataFrame(
        {
            "Open": [100.0, 100.0, 101.0, 101.0, 100.0, 99.5, 99.0],
            "High": [100.5, 100.5, 101.5, 101.5, 100.5, 100.0, 99.5],
            "Low": [99.5, 99.5, 100.5, 100.5, 99.5, 99.0, 98.5],
            "Close": [100.0, 100.0, 101.0, 101.0, 100.0, 99.5, 99.0],
            "Volume": [1000] * length,
        },
        index=index,
    )
    signals = {
        "long_entries": pd.Series(
            [False, True, False, False, False, False, False], index=index
        ),
        "sl_long": pd.Series(
            [np.nan, 95.0, 95.0, 95.0, 95.0, 95.0, 95.0], index=index
        ),
        # fast_hma_exit fires bar 3, but no HW cross same bar → exit not
        # triggered.  move_to_be_on_fast_hma_cross moves SL → entry and sets
        # tp1_hit.  Bar 4 low touches entry → Breakeven.
        "fast_hma_exit_long": pd.Series(
            [False, False, False, True, False, False, False], index=index
        ),
        "hw_cross_over": pd.Series([False] * length, index=index),
    }
    result = _simulate_v4(df, signals, move_to_be_on_fast_hma_cross=True)
    assert len(result["trades"]) == 1
    trade = result["trades"][0]
    assert trade["status"] == "Breakeven"
    assert trade["exit_price"] == 100.0


def test_v4_early_exit_fired_off_mode_matches_v3_behaviour():
    """When entry happens with hma1 already > BBMC_ssl (early_exit_fired=True)
    and early_exit_fired_mode='off', the V4 simulator must NOT pre-arm
    pending_final_exit at entry — equivalent to V3 (where the signal is
    simply lost)."""
    length = 6
    index = pd.date_range(
        "2024-01-01", periods=length, freq="5min", tz="Europe/Brussels"
    )
    df = pd.DataFrame(
        {
            "Open": [100.0, 100.0, 101.0, 101.0, 101.0, 101.0],
            "High": [100.5, 100.5, 101.5, 101.5, 101.5, 101.5],
            "Low": [99.5, 99.5, 100.5, 100.5, 100.5, 100.5],
            "Close": [100.0, 100.0, 101.0, 101.0, 101.0, 101.0],
            "Volume": [1000] * length,
        },
        index=index,
    )
    signals = {
        "long_entries": pd.Series(
            [False, True, False, False, False, False], index=index
        ),
        "sl_long": pd.Series([np.nan, 95.0, 95.0, 95.0, 95.0, 95.0], index=index),
        # hma1 already above BBMC at entry bar 1 → early_exit_fired.
        "hma1_above_ssl": pd.Series(
            [False, True, True, True, True, True], index=index
        ),
        # No fast_hma cross fires (already past it).  HW cross at bar 3.
        "fast_hma_exit_long": pd.Series([False] * length, index=index),
        "hw_cross_over": pd.Series(
            [False, False, False, True, False, False], index=index
        ),
    }
    # "off" mode → no pre-arm → no exit on the HW cross → position carries to end.
    off_result = _simulate_v4(df, signals, early_exit_fired_mode="off")
    assert len(off_result["trades"]) == 1
    assert off_result["trades"][0]["status"] == "End of Data"

    # "hw_rr" mode → pre-arms pending → exits on the HW cross.
    hw_result = _simulate_v4(df, signals, early_exit_fired_mode="hw_rr")
    assert len(hw_result["trades"]) == 1
    assert hw_result["trades"][0]["status"] == "Canal Exit"


def test_v4_with_default_params_reproduces_v3_default_trades_end_to_end():
    """End-to-end: V4 with default params produces the same trade list as
    V3 with default params on a real MNQ slice. Skipped if the data file
    isn't present in the dev environment."""
    import pytest

    market_csv = os.path.join(
        os.path.dirname(__file__), "..", "data", "market_data", "MNQ", "MNQ_5m.csv"
    )
    if not os.path.exists(market_csv):
        pytest.skip("MNQ market data not available in this environment")

    from scripts.goals._shared.harness import run_backtest

    r3 = run_backtest(
        strategy_name="HMASSLOsciV3",
        symbol="MNQ",
        interval="5m",
        start="2025-12-01",
        end="2025-12-10",
    )
    r4 = run_backtest(
        strategy_name="HMASSLOsciV4",
        symbol="MNQ",
        interval="5m",
        start="2025-12-01",
        end="2025-12-10",
    )

    def key(t):
        return (
            t["entry_time"],
            t["exit_time"],
            t["side"],
            round(t["entry_price"], 4),
            round(t["exit_price"], 4),
            round(t["pnl"], 4),
        )

    assert [key(t) for t in r3["trades"]] == [key(t) for t in r4["trades"]]


def test_v4_early_exit_canal_inverse_mode_exits_on_canal_break():
    """early_exit_fired_mode='canal_inverse' → close < canalLower (long)
    triggers an immediate exit."""
    length = 6
    index = pd.date_range(
        "2024-01-01", periods=length, freq="5min", tz="Europe/Brussels"
    )
    df = pd.DataFrame(
        {
            "Open": [100.0, 100.0, 100.0, 99.0, 98.0, 97.0],
            "High": [100.5, 100.5, 100.5, 99.5, 98.5, 97.5],
            "Low": [99.5, 99.5, 99.5, 98.5, 97.5, 96.5],
            "Close": [100.0, 100.0, 100.0, 99.0, 98.0, 97.0],
            "Volume": [1000] * length,
        },
        index=index,
    )
    canal_lower = pd.Series([97.0] * length, index=index)
    canal_upper = pd.Series([105.0] * length, index=index)

    signals = {
        "long_entries": pd.Series(
            [False, True, False, False, False, False], index=index
        ),
        "sl_long": pd.Series([np.nan, 90.0, 90.0, 90.0, 90.0, 90.0], index=index),
        "hma1_above_ssl": pd.Series(
            [True, True, True, True, True, True], index=index
        ),
        "fast_hma_exit_long": pd.Series([False] * length, index=index),
        "hw_cross_over": pd.Series([False] * length, index=index),
    }
    result = _simulate_v4(
        df,
        signals,
        canal_lower=canal_lower,
        canal_upper=canal_upper,
        early_exit_fired_mode="canal_inverse",
    )
    # Bar 5 close=97 < canal_lower=97? Not strictly. 96.5? canal_lower stays
    # 97 → close=97 is NOT below. Bar 5 close=97; canal_lower=97; 97 < 97 is
    # False.  But our data has close drifting; the position closes via
    # canal_inverse only when close strictly breaks.  Let me check bar-by-bar:
    # bar 1 close=100 (entry).  bar 2 close=100. bar 3 close=99.  bar 4
    # close=98. bar 5 close=97. None below 97 → no canal_inverse exit fires →
    # End of Data.
    #
    # To actually fire, push close below 97 on the last bar.
    df.loc[index[-1], "Close"] = 96.5
    df.loc[index[-1], "Low"] = 96.0
    result = _simulate_v4(
        df,
        signals,
        canal_lower=canal_lower,
        canal_upper=canal_upper,
        early_exit_fired_mode="canal_inverse",
    )
    assert len(result["trades"]) == 1
    assert result["trades"][0]["status"] == "Canal Exit"
