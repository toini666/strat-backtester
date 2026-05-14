"""Tests for the HMA-SSL-Osci v3 strategy.

These cover the behaviours that distinguish v3 from v2:

* entry trigger is the HMA-slow / SSL-baseline cross with an N-bar window
* exit trigger is the HMA-fast / SSL-baseline counter-cross
* ``loss_exit_blocked`` latches and arms the canal-break fallback
* ``one_trade_per_setup_window`` blocks re-entries inside the same window
* the HW-based SL uses ``lowest(low, ...)`` from the last valid HW cross
"""

import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.engine.simulator import SimulatorConfig, _Position, simulate
from src.strategies.hma_ssl_osci_v3 import HMASSLOsciV3


def _base_params() -> dict:
    p = HMASSLOsciV3().default_params.copy()
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
            "signal_candle_sl_on": False,
            "hw_partial_pct": 0.0,
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


def _install_fake_indicators(
    monkeypatch,
    data: pd.DataFrame,
    *,
    hma1: pd.Series,
    hma2: pd.Series,
    bbmc: pd.Series,
    hw_cross_over_idx=None,
    hw_cross_under_idx=None,
):
    """Stub the heavy indicator helpers so the test controls every value."""
    length = len(data)
    index = data.index
    src_ema = pd.Series(np.full(length, 100.0), index=index)
    canal_upper = pd.Series(np.maximum(hma1.values, hma2.values), index=index)
    canal_lower = pd.Series(np.minimum(hma1.values, hma2.values), index=index)
    canal_green = pd.Series(hma1.values > hma2.values, index=index)

    ssl_upper = pd.Series(bbmc.values + 1.0, index=index)
    ssl_lower = pd.Series(bbmc.values - 1.0, index=index)

    # Craft osc_sig / osc_sgd so that ta.crossover(sig, sgd) fires at the
    # bars requested by the test.  We do it by toggling sign on adjacent bars.
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
        HMASSLOsciV3,
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
        HMASSLOsciV3,
        "_compute_ssl",
        staticmethod(lambda close, high, low, length, mult: (bbmc, ssl_upper, ssl_lower)),
    )
    monkeypatch.setattr(
        HMASSLOsciV3,
        "_compute_oscillator",
        staticmethod(lambda close, high, low, hl2, mL, sT, sL: (osc_sig_s, osc_sgd_s)),
    )
    monkeypatch.setattr(
        HMASSLOsciV3,
        "_compute_mfi",
        staticmethod(lambda hl2, volume, mfL, mfS: mfi),
    )
    monkeypatch.setattr(
        HMASSLOsciV3,
        "_compute_mfi_cloud",
        staticmethod(
            lambda mfi_values, mfL: (cloud_long, cloud_short, cloud_ref, cloud_line)
        ),
    )


def test_v3_emits_slow_hma_ssl_cross_and_fast_exit(monkeypatch):
    """hma2 crosses below bbmc → long setup; hma1 later crosses above bbmc → exit signal."""
    length = 48
    data = _build_data(length)

    # Build the indicator series:
    # * hma2 is above bbmc until bar 30, then below from bar 30 → slow_cross_long at 30.
    # * hma1 starts above hma2 (so canal_green=True / "red HMA visually"),
    #   then dips below bbmc at bar 20 and pops back above at bar 35 → fast_exit_long at 35.
    hma1 = np.full(length, 102.0)
    hma2 = np.full(length, 101.5)
    bbmc = np.full(length, 100.0)

    # Slow HMA cross long at bar 30: hma2 was above bbmc, falls below.
    hma2[30:] = 99.0

    # Fast HMA cross long-exit at bar 35: hma1 below bbmc on bar 34, above on bar 35.
    hma1[34] = 99.5
    hma1[35:] = 101.0

    hw_low_idx = list(range(20, 30, 2))  # HW crossovers seeded > 2 bars before bar 30
    _install_fake_indicators(
        monkeypatch,
        data,
        hma1=pd.Series(hma1, index=data.index),
        hma2=pd.Series(hma2, index=data.index),
        bbmc=pd.Series(bbmc, index=data.index),
        hw_cross_over_idx=hw_low_idx,
    )

    sigs = HMASSLOsciV3().generate_signals(data.copy(), _base_params())

    assert sigs["fast_hma_exit_long"].iloc[35]
    # bar 30 is the long setup bar (slow cross long)
    assert int(sigs["setup_bar_long"].iloc[30]) == 30
    # window still open at bar 35 (offset 5 ≤ entry_window_bars=5)
    assert int(sigs["setup_bar_long"].iloc[35]) == 30


def test_v3_partial_close_and_loss_exit_blocked_via_simulator():
    """End-to-end: a long enters, a fast-HMA exit fires in loss → loss_exit_blocked
    latches; on a later bar a close out of canal triggers the fallback exit."""
    length = 6
    index = pd.date_range("2024-01-01", periods=length, freq="5min", tz="Europe/Brussels")
    df = pd.DataFrame(
        {
            "Open": [100.0, 100.0, 100.0, 99.0, 98.5, 97.0],
            "High": [100.5, 100.5, 100.5, 99.5, 99.0, 97.5],
            "Low": [99.5, 99.5, 99.5, 98.5, 97.5, 96.5],
            "Close": [100.0, 100.0, 100.0, 99.0, 98.5, 97.0],
            "Volume": [1000] * length,
        },
        index=index,
    )

    canal_upper = pd.Series([101.0, 101.0, 101.0, 101.0, 100.0, 99.5], index=index)
    canal_lower = pd.Series([99.0, 99.0, 99.0, 99.0, 98.0, 97.5], index=index)

    signals = {
        "long_entries": pd.Series(
            [False, True, False, False, False, False], index=index
        ),
        "short_entries": pd.Series([False] * length, index=index),
        "sl_long": pd.Series([np.nan, 95.0, 95.0, 95.0, 95.0, 95.0], index=index),
        "sl_short": pd.Series([np.nan] * length, index=index),
        "tp1_long": pd.Series([np.nan] * length, index=index),
        "tp1_short": pd.Series([np.nan] * length, index=index),
        "disable_price_tp1": True,
        # Fast-HMA exit fires on bar 3 → arms pendingFinalExit.  A confirmed
        # hyperwave cross on the same bar lifts the gate, but the trade is
        # in loss so the exit is blocked and ``loss_exit_blocked`` latches.
        "fast_hma_exit_long": pd.Series(
            [False, False, False, True, False, False], index=index
        ),
        "fast_hma_exit_short": pd.Series([False] * length, index=index),
        "hw_cross_over": pd.Series(
            [False, False, False, True, False, False], index=index
        ),
        "hw_cross_under": pd.Series([False] * length, index=index),
        "canal_lower": canal_lower,
        "canal_upper": canal_upper,
        "canal_green": pd.Series([False] * length, index=index),
        "setup_bar_long": pd.Series([1] * length, index=index),
        "setup_bar_short": pd.Series([-1] * length, index=index),
        "ema_main": pd.Series([100.0] * length, index=index),
        "ema_secondary": pd.Series([100.0] * length, index=index),
    }

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
        tp1_partial_pct=0.25,
        tp2_partial_pct=0.0,
        canal_exit_mode="v3_fast_hma_ssl",
        block_loss_canal_exit_before_tp1=True,
    )

    result = simulate(df, df, signals, cfg, signals["ema_main"], signals["ema_secondary"])
    trades = result["trades"]
    assert len(trades) == 1
    trade = trades[0]
    # The trade entered on bar 1.  Bar 3 fast-HMA exit + hyperwave cross is in
    # loss (close=99 < entry=100) so the simulator must NOT close on bar 3.
    # Bar 4 has close (98.5) above canal_lower (98.0), so still no fallback.
    # Bar 5: close=97.0 < canal_lower=97.5 → fallback exit.
    assert trade["status"] == "Canal Exit"
    assert pd.Timestamp(trade["exit_execution_time"]) >= index[4]


def test_v3_one_trade_per_setup_window_blocks_reentry():
    """If a long trade closes via SL inside the entry window, a second long
    entry on the same setup must be suppressed."""
    length = 7
    index = pd.date_range("2024-01-01", periods=length, freq="5min", tz="Europe/Brussels")
    df = pd.DataFrame(
        {
            "Open": [100.0] * length,
            "High": [100.5, 100.5, 100.5, 99.0, 99.0, 100.5, 100.5],
            # Bar 3 dips below SL=95 ⇒ stop hit.
            "Low": [99.5, 99.5, 99.5, 94.0, 98.0, 99.5, 99.5],
            "Close": [100.0, 100.0, 100.0, 95.5, 99.5, 100.0, 100.0],
            "Volume": [1000] * length,
        },
        index=index,
    )

    setup_bar = pd.Series([1, 1, 1, 1, 1, 1, 1], index=index)

    signals = {
        # Long entries at bars 2 and 5.  With one_trade_per_setup_window=True,
        # only the first one (bar 2) should be taken because bar 5 shares
        # setup_bar == 1.
        "long_entries": pd.Series(
            [False, False, True, False, False, True, False], index=index
        ),
        "short_entries": pd.Series([False] * length, index=index),
        "sl_long": pd.Series([np.nan, np.nan, 95.0, np.nan, np.nan, 95.0, np.nan], index=index),
        "sl_short": pd.Series([np.nan] * length, index=index),
        "tp1_long": pd.Series([np.nan] * length, index=index),
        "tp1_short": pd.Series([np.nan] * length, index=index),
        "disable_price_tp1": True,
        "fast_hma_exit_long": pd.Series([False] * length, index=index),
        "fast_hma_exit_short": pd.Series([False] * length, index=index),
        "canal_lower": pd.Series([99.0] * length, index=index),
        "canal_upper": pd.Series([101.0] * length, index=index),
        "setup_bar_long": setup_bar,
        "setup_bar_short": pd.Series([-1] * length, index=index),
        "ema_main": pd.Series([100.0] * length, index=index),
        "ema_secondary": pd.Series([100.0] * length, index=index),
    }

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
        canal_exit_mode="v3_fast_hma_ssl",
        one_trade_per_setup_window=True,
    )

    result = simulate(df, df, signals, cfg, signals["ema_main"], signals["ema_secondary"])
    trades = result["trades"]
    # Only the first entry should have been taken; the bar-5 re-entry is blocked.
    assert len(trades) == 1
    assert trades[0]["status"] == "Stop Loss"


def test_v3_canal_fallback_uses_strict_less_than(monkeypatch):
    """Boundary check: ``close == canal_lower`` must NOT trigger the
    canal-break fallback while ``loss_exit_blocked`` is latched."""
    length = 6
    index = pd.date_range("2024-01-01", periods=length, freq="5min", tz="Europe/Brussels")
    df = pd.DataFrame(
        {
            "Open": [100.0, 100.0, 100.0, 99.0, 99.0, 96.5],
            "High": [100.5, 100.5, 100.5, 99.5, 99.5, 97.0],
            "Low": [99.5, 99.5, 99.5, 98.5, 98.5, 96.0],
            # Bar 4 closes EXACTLY at canal_lower → must not exit yet.
            # Bar 5 closes below → exit.
            "Close": [100.0, 100.0, 100.0, 99.0, 99.0, 96.5],
            "Volume": [1000] * length,
        },
        index=index,
    )
    canal_lower = pd.Series([99.0, 99.0, 99.0, 99.0, 99.0, 97.0], index=index)
    canal_upper = pd.Series([101.0] * length, index=index)

    signals = {
        "long_entries": pd.Series(
            [False, True, False, False, False, False], index=index
        ),
        "short_entries": pd.Series([False] * length, index=index),
        "sl_long": pd.Series([np.nan, 95.0, 95.0, 95.0, 95.0, 95.0], index=index),
        "sl_short": pd.Series([np.nan] * length, index=index),
        "tp1_long": pd.Series([np.nan] * length, index=index),
        "tp1_short": pd.Series([np.nan] * length, index=index),
        "disable_price_tp1": True,
        "fast_hma_exit_long": pd.Series(
            [False, False, False, True, False, False], index=index
        ),
        "fast_hma_exit_short": pd.Series([False] * length, index=index),
        # Same-bar hyperwave cross lifts the v3 exit gate on bar 3.
        "hw_cross_over": pd.Series(
            [False, False, False, True, False, False], index=index
        ),
        "hw_cross_under": pd.Series([False] * length, index=index),
        "canal_lower": canal_lower,
        "canal_upper": canal_upper,
        "setup_bar_long": pd.Series([1] * length, index=index),
        "setup_bar_short": pd.Series([-1] * length, index=index),
        "ema_main": pd.Series([100.0] * length, index=index),
        "ema_secondary": pd.Series([100.0] * length, index=index),
    }
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
        tp1_partial_pct=0.25,
        tp2_partial_pct=0.0,
        canal_exit_mode="v3_fast_hma_ssl",
        block_loss_canal_exit_before_tp1=True,
    )
    result = simulate(df, df, signals, cfg, signals["ema_main"], signals["ema_secondary"])
    trades = result["trades"]
    assert len(trades) == 1
    assert pd.Timestamp(trades[0]["exit_execution_time"]) >= index[5]


def test_v3_partial_then_fast_hma_exit_closes_in_profit():
    """End-to-end ordering: HW partial first, fast-HMA exit later on a
    bar that stays above breakeven so intra-bar BE does not pre-empt the
    canal exit.  Verifies both legs are present and the close fires."""
    length = 7
    index = pd.date_range("2024-01-01", periods=length, freq="5min", tz="Europe/Brussels")
    df = pd.DataFrame(
        {
            "Open":  [100.0, 100.0, 100.0, 101.0, 102.0, 101.0, 100.7],
            "High":  [100.5, 100.5, 100.5, 101.5, 102.5, 101.5, 101.2],
            # Bar 5 stays strictly above BE=100 (low=100.5 > 100), so BE
            # does not fire intra-bar even though tp1_hit is True.
            "Low":   [ 99.5,  99.5,  99.5, 100.5, 101.5, 100.5, 100.2],
            "Close": [100.0, 100.0, 100.0, 101.0, 102.0, 101.0, 100.7],
            "Volume": [1000] * length,
        },
        index=index,
    )
    signals = {
        "long_entries": pd.Series(
            [False, True, False, False, False, False, False], index=index
        ),
        "short_entries": pd.Series([False] * length, index=index),
        "sl_long": pd.Series([np.nan, 95.0, 95.0, 95.0, 95.0, 95.0, 95.0], index=index),
        "sl_short": pd.Series([np.nan] * length, index=index),
        "tp1_long": pd.Series([np.nan] * length, index=index),
        "tp1_short": pd.Series([np.nan] * length, index=index),
        "disable_price_tp1": True,
        # Bar 4: HW partial signal — close=102 > entry=100 → partial fires
        "partial_close_long": pd.Series(
            [False, False, False, False, True, False, False], index=index
        ),
        "partial_close_short": pd.Series([False] * length, index=index),
        # Bar 5: fast-HMA exit, close=101, low=100.5 (above BE=100)
        "fast_hma_exit_long": pd.Series(
            [False, False, False, False, False, True, False], index=index
        ),
        "fast_hma_exit_short": pd.Series([False] * length, index=index),
        # Bar 4: hw_cross_under fires (drives the partial).  Bar 5: confirmed
        # hyperwave cross gates the v3 final exit.
        "hw_cross_over": pd.Series(
            [False, False, False, False, False, True, False], index=index
        ),
        "hw_cross_under": pd.Series(
            [False, False, False, False, True, False, False], index=index
        ),
        "canal_lower": pd.Series([99.5] * length, index=index),
        "canal_upper": pd.Series([102.5] * length, index=index),
        "setup_bar_long": pd.Series([1] * length, index=index),
        "setup_bar_short": pd.Series([-1] * length, index=index),
        "ema_main": pd.Series([100.0] * length, index=index),
        "ema_secondary": pd.Series([100.0] * length, index=index),
    }
    cfg = SimulatorConfig(
        initial_equity=50000,
        risk_per_trade=0.01,
        max_contracts=50,
        tick_size=0.25,
        tick_value=0.5,
        point_value=2.0,
        fee_per_trade=0.0,
        auto_close_enabled=False,
        blackout_windows=[],
        cooldown_bars=0,
        tp1_execution_mode="touch",
        tp1_partial_pct=0.25,
        tp2_partial_pct=0.0,
        canal_exit_mode="v3_fast_hma_ssl",
        block_loss_canal_exit_before_tp1=True,
    )
    result = simulate(df, df, signals, cfg, signals["ema_main"], signals["ema_secondary"])
    trades = result["trades"]
    assert len(trades) == 1
    trade = trades[0]
    assert trade["status"] == "Canal Exit"
    leg_statuses = [leg["status"] for leg in trade["legs"]]
    assert any(s.startswith("TP_HW") for s in leg_statuses), leg_statuses
    assert pd.Timestamp(trade["exit_execution_time"]) == index[6]


def test_v3_hw_sl_falls_back_to_previous_cross_within_lookaround(monkeypatch):
    """When the latest HW crossover is too fresh (age ≤ 2) and there is no
    previous one, the SL must be NaN and the strategy must NOT emit an entry."""
    length = 36
    data = _build_data(length)
    # hma2 stays above bbmc until bar 30, then drops below → slow_cross_long at 30.
    hma1 = np.full(length, 102.0)
    hma2 = np.full(length, 101.5)
    bbmc = np.full(length, 100.0)
    hma2[30:] = 99.0

    # Only one HW crossover, on bar 29 (one bar before the setup). Age at the
    # bar where we'd enter (≥ 30) is therefore ≤ 1 ≤ HW_SL_LOOKAROUND=2 →
    # SL falls back to prev_bull_hw_bar which is None → no SL → no entry.
    _install_fake_indicators(
        monkeypatch,
        data,
        hma1=pd.Series(hma1, index=data.index),
        hma2=pd.Series(hma2, index=data.index),
        bbmc=pd.Series(bbmc, index=data.index),
        hw_cross_over_idx=[29],
    )
    sigs = HMASSLOsciV3().generate_signals(data.copy(), _base_params())
    # Setup bar should be 30, but the entry on bar 30 must be rejected for
    # lack of a valid HW-based SL.
    assert int(sigs["setup_bar_long"].iloc[30]) == 30
    assert not bool(sigs["long_entries"].iloc[30])
    assert np.isnan(sigs["sl_long"].iloc[30])


def test_v3_pending_final_exit_waits_for_next_hyperwave():
    """A fast-HMA / SSL cross arms ``pending_final_exit`` but the position
    must stay open until the next confirmed hyperwave cross.  Once it
    arrives — even several bars later — the position closes on that bar."""
    length = 8
    index = pd.date_range("2024-01-01", periods=length, freq="5min", tz="Europe/Brussels")
    df = pd.DataFrame(
        {
            "Open":  [100.0, 100.0, 100.0, 101.0, 101.5, 101.5, 101.5, 101.5],
            "High":  [100.5, 100.5, 100.5, 101.5, 102.0, 102.0, 102.0, 102.0],
            # All lows stay above BE=100 so intra-bar BE never pre-empts the
            # canal exit.
            "Low":   [ 99.5,  99.5,  99.5, 100.5, 101.0, 101.0, 101.0, 101.0],
            "Close": [100.0, 100.0, 100.0, 101.0, 101.5, 101.5, 101.5, 101.5],
            "Volume": [1000] * length,
        },
        index=index,
    )

    signals = {
        "long_entries": pd.Series(
            [False, True, False, False, False, False, False, False], index=index
        ),
        "short_entries": pd.Series([False] * length, index=index),
        "sl_long": pd.Series([np.nan, 95.0, 95.0, 95.0, 95.0, 95.0, 95.0, 95.0], index=index),
        "sl_short": pd.Series([np.nan] * length, index=index),
        "tp1_long": pd.Series([np.nan] * length, index=index),
        "tp1_short": pd.Series([np.nan] * length, index=index),
        "disable_price_tp1": True,
        # Fast-HMA exit on bar 3 arms pendingFinalExit but no hyperwave cross
        # there, so the position must stay open.
        "fast_hma_exit_long": pd.Series(
            [False, False, False, True, False, False, False, False], index=index
        ),
        "fast_hma_exit_short": pd.Series([False] * length, index=index),
        # Confirmed hyperwave cross arrives only on bar 6 → exit there.
        "hw_cross_over": pd.Series(
            [False, False, False, False, False, False, True, False], index=index
        ),
        "hw_cross_under": pd.Series([False] * length, index=index),
        "canal_lower": pd.Series([99.0] * length, index=index),
        "canal_upper": pd.Series([102.5] * length, index=index),
        "setup_bar_long": pd.Series([1] * length, index=index),
        "setup_bar_short": pd.Series([-1] * length, index=index),
        "ema_main": pd.Series([100.0] * length, index=index),
        "ema_secondary": pd.Series([100.0] * length, index=index),
    }

    cfg = SimulatorConfig(
        initial_equity=50000,
        risk_per_trade=0.01,
        max_contracts=50,
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
        canal_exit_mode="v3_fast_hma_ssl",
        block_loss_canal_exit_before_tp1=True,
    )

    result = simulate(df, df, signals, cfg, signals["ema_main"], signals["ema_secondary"])
    trades = result["trades"]
    assert len(trades) == 1
    trade = trades[0]
    assert trade["status"] == "Canal Exit"
    # Exit fires on bar 6 → exec time is the next bar's open.
    assert pd.Timestamp(trade["exit_execution_time"]) == index[7]


def test_v3_delta_filter_both_off_falls_back_to_mfi(monkeypatch):
    """Filter ⑥ with both deltas off requires the contrarian MFI condition
    (mfi < 0 for long, mfi > 0 for short)."""
    length = 36
    data = _build_data(length)
    # Keep hma1 < hma2 throughout so canal stays red (cg=False) and the
    # ``hma_long_ok = not cg`` branch lets entries through regardless of
    # the polarity-recency check.
    hma1 = np.full(length, 98.0)
    hma2 = np.full(length, 101.5)
    bbmc = np.full(length, 100.0)
    hma2[30:] = 99.0  # slow_cross_long on bar 30

    # Seed HW crosses well before bar 30 so the SL window is valid.
    _install_fake_indicators(
        monkeypatch,
        data,
        hma1=pd.Series(hma1, index=data.index),
        hma2=pd.Series(hma2, index=data.index),
        bbmc=pd.Series(bbmc, index=data.index),
        hw_cross_over_idx=list(range(20, 28, 2)),
    )

    # Force osc_sig = 0 at the entry bar so both deltas are off.
    def _zero_osc(close, high, low, hl2, mL, sT, sL):
        osc_sig = np.zeros(length)
        osc_sgd = np.zeros(length)
        for k in range(20, 28, 2):
            osc_sig[k - 1] = -1.0
            osc_sgd[k - 1] = 1.0
            osc_sig[k] = 1.0
            osc_sgd[k] = -1.0
        return (
            pd.Series(osc_sig, index=data.index),
            pd.Series(osc_sgd, index=data.index),
        )

    monkeypatch.setattr(HMASSLOsciV3, "_compute_oscillator", staticmethod(_zero_osc))

    # Case A: mfi > 0 with i_deltaOn=True → long blocked (both deltas off,
    # but the contrarian MFI condition for long (mfi < 0) is not met).
    monkeypatch.setattr(
        HMASSLOsciV3,
        "_compute_mfi",
        staticmethod(lambda hl2, volume, mfL, mfS: pd.Series(
            np.full(length, 5.0), index=data.index
        )),
    )
    params = _base_params()
    params["delta_on"] = True
    sigs = HMASSLOsciV3().generate_signals(data.copy(), params)
    assert not bool(sigs["long_entries"].iloc[30])

    # Case B: mfi < 0 with i_deltaOn=True → long allowed by the ⑥ fallback.
    monkeypatch.setattr(
        HMASSLOsciV3,
        "_compute_mfi",
        staticmethod(lambda hl2, volume, mfL, mfS: pd.Series(
            np.full(length, -5.0), index=data.index
        )),
    )
    sigs = HMASSLOsciV3().generate_signals(data.copy(), params)
    assert bool(sigs["long_entries"].iloc[30])


def test_v3_one_trade_per_setup_window_off_allows_reentry():
    """Sanity: with the v3 filter disabled, the simulator does re-enter on
    the second signal within the same setup window."""
    length = 7
    index = pd.date_range("2024-01-01", periods=length, freq="5min", tz="Europe/Brussels")
    df = pd.DataFrame(
        {
            "Open": [100.0] * length,
            "High": [100.5, 100.5, 100.5, 99.0, 99.0, 100.5, 100.5],
            "Low": [99.5, 99.5, 99.5, 94.0, 98.0, 99.5, 99.5],
            "Close": [100.0, 100.0, 100.0, 95.5, 99.5, 100.0, 100.0],
            "Volume": [1000] * length,
        },
        index=index,
    )

    setup_bar = pd.Series([1, 1, 1, 1, 1, 1, 1], index=index)

    signals = {
        "long_entries": pd.Series(
            [False, False, True, False, False, True, False], index=index
        ),
        "short_entries": pd.Series([False] * length, index=index),
        "sl_long": pd.Series([np.nan, np.nan, 95.0, np.nan, np.nan, 95.0, np.nan], index=index),
        "sl_short": pd.Series([np.nan] * length, index=index),
        "tp1_long": pd.Series([np.nan] * length, index=index),
        "tp1_short": pd.Series([np.nan] * length, index=index),
        "disable_price_tp1": True,
        "fast_hma_exit_long": pd.Series([False] * length, index=index),
        "fast_hma_exit_short": pd.Series([False] * length, index=index),
        "canal_lower": pd.Series([99.0] * length, index=index),
        "canal_upper": pd.Series([101.0] * length, index=index),
        "setup_bar_long": setup_bar,
        "setup_bar_short": pd.Series([-1] * length, index=index),
        "ema_main": pd.Series([100.0] * length, index=index),
        "ema_secondary": pd.Series([100.0] * length, index=index),
    }

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
        canal_exit_mode="v3_fast_hma_ssl",
        one_trade_per_setup_window=False,
    )

    result = simulate(df, df, signals, cfg, signals["ema_main"], signals["ema_secondary"])
    trades = result["trades"]
    assert len(trades) == 2
