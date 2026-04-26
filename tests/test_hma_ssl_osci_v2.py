import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.strategies.hma_ssl_osci import HMASSLOsci
from src.strategies.hma_ssl_osci_v2 import HMASSLOsciV2


def _build_data(length: int = 48) -> pd.DataFrame:
    index = pd.date_range("2024-01-01", periods=length, freq="5min", tz="Europe/Brussels")
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


def _params():
    strategy = HMASSLOsciV2()
    params = strategy.default_params.copy()
    params.update(
        {
            "ema_len": 2,
            "hma1_len": 2,
            "hma2_len": 3,
            "hma_pol_bars": 3,
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
            "sl_mode": "cross_hma",
            "hw_partial_pct": 25.0,
        }
    )
    return params


def _install_fake_indicators(
    monkeypatch,
    data: pd.DataFrame,
    *,
    signal_idx: int,
    close_signal: float,
    canal_upper_signal: float,
    canal_lower_signal: float,
    bbmc_signal: float,
    ssl_upper_signal: float,
    ssl_lower_signal: float,
    signal_canal_green: bool = False,
    flip_direction: str = "up",
    flip_gap: int = 6,
    flip_avg: float = 95.0,
):
    length = len(data)
    index = data.index

    data.loc[index[signal_idx], "Close"] = close_signal
    data.loc[index[signal_idx], "Open"] = close_signal
    data.loc[index[signal_idx], "High"] = close_signal + 0.5
    data.loc[index[signal_idx], "Low"] = close_signal - 0.5

    src_ema = pd.Series(np.full(length, 100.0), index=index)
    hma1 = pd.Series(np.full(length, 94.0), index=index)
    hma2 = pd.Series(np.full(length, 96.0), index=index)

    flip_idx = signal_idx - flip_gap
    if flip_direction == "up":
        hma1.iloc[:flip_idx] = flip_avg - 1.0
        hma2.iloc[:flip_idx] = flip_avg + 1.0
        hma1.iloc[flip_idx:] = flip_avg + 1.0
        hma2.iloc[flip_idx:] = flip_avg - 1.0
    else:
        hma1.iloc[:flip_idx] = flip_avg + 1.0
        hma2.iloc[:flip_idx] = flip_avg - 1.0
        hma1.iloc[flip_idx:] = flip_avg - 1.0
        hma2.iloc[flip_idx:] = flip_avg + 1.0

    if signal_canal_green:
        hma1.iloc[signal_idx] = canal_upper_signal
        hma2.iloc[signal_idx] = canal_lower_signal
    else:
        hma1.iloc[signal_idx] = canal_lower_signal
        hma2.iloc[signal_idx] = canal_upper_signal

    canal_upper = pd.Series(np.maximum(hma1.values, hma2.values), index=index)
    canal_lower = pd.Series(np.minimum(hma1.values, hma2.values), index=index)
    canal_green = pd.Series(hma1.values > hma2.values, index=index)

    bbmc = pd.Series(np.full(length, 100.0), index=index)
    ssl_upper = pd.Series(np.full(length, 101.0), index=index)
    ssl_lower = pd.Series(np.full(length, 98.0), index=index)
    bbmc.iloc[signal_idx] = bbmc_signal
    ssl_upper.iloc[signal_idx] = ssl_upper_signal
    ssl_lower.iloc[signal_idx] = ssl_lower_signal

    osc_sig = pd.Series(np.zeros(length), index=index)
    osc_sgd = pd.Series(np.zeros(length), index=index)
    mfi = pd.Series(np.zeros(length), index=index)
    cloud_long = np.zeros(length, dtype=bool)
    cloud_short = np.zeros(length, dtype=bool)
    cloud_ref = np.full(length, np.nan)
    cloud_line = np.full(length, np.nan)

    for cls in (HMASSLOsci, HMASSLOsciV2):
        monkeypatch.setattr(
            cls,
            "_compute_hma_canal_full",
            staticmethod(lambda close, ema_len, hma1_len, hma2_len, amp_mult: (
                src_ema,
                hma1,
                hma2,
                canal_upper,
                canal_lower,
                canal_green,
            )),
        )
        monkeypatch.setattr(
            cls,
            "_compute_ssl",
            staticmethod(lambda close, high, low, length, mult: (bbmc, ssl_upper, ssl_lower)),
        )
        monkeypatch.setattr(
            cls,
            "_compute_oscillator",
            staticmethod(lambda close, high, low, hl2, mL, sT, sL: (osc_sig, osc_sgd)),
        )
        monkeypatch.setattr(
            cls,
            "_compute_mfi",
            staticmethod(lambda hl2, volume, mfL, mfS: mfi),
        )
        monkeypatch.setattr(
            cls,
            "_compute_mfi_cloud",
            staticmethod(lambda mfi_values, mfL: (cloud_long, cloud_short, cloud_ref, cloud_line)),
        )


def test_hma_ssl_osci_v2_uses_counter_hma_polarity_without_v1_ssl_gate(monkeypatch):
    data = _build_data()
    params = _params()
    signal_idx = 30

    _install_fake_indicators(
        monkeypatch,
        data,
        signal_idx=signal_idx,
        close_signal=101.0,
        canal_upper_signal=110.0,
        canal_lower_signal=100.0,
        bbmc_signal=100.0,
        ssl_upper_signal=100.5,
        ssl_lower_signal=98.0,
        signal_canal_green=False,
        flip_direction="down",
        flip_gap=6,
        flip_avg=95.0,
    )

    v1 = HMASSLOsci().generate_signals(data.copy(), params)
    v2 = HMASSLOsciV2().generate_signals(data.copy(), params)

    assert not v1["long_entries"].iloc[signal_idx]
    assert np.isnan(v1["sl_long"].iloc[signal_idx])
    assert v2["long_entries"].iloc[signal_idx]
    assert v2["sl_long"].iloc[signal_idx] == 95.0


def test_hma_ssl_osci_v2_allows_recent_bullish_hma_polarity(monkeypatch):
    data = _build_data()
    params = _params()
    signal_idx = 30

    _install_fake_indicators(
        monkeypatch,
        data,
        signal_idx=signal_idx,
        close_signal=112.0,
        canal_upper_signal=110.0,
        canal_lower_signal=101.0,
        bbmc_signal=100.0,
        ssl_upper_signal=100.5,
        ssl_lower_signal=98.0,
        signal_canal_green=True,
        flip_direction="up",
        flip_gap=2,
        flip_avg=95.0,
    )

    v2 = HMASSLOsciV2().generate_signals(data.copy(), params)

    assert v2["long_entries"].iloc[signal_idx]
    assert v2["sl_long"].iloc[signal_idx] == 95.0


def test_hma_ssl_osci_v2_uses_shared_last_hma_cross_level_for_stop(monkeypatch):
    data = _build_data()
    params = _params()
    signal_idx = 30

    _install_fake_indicators(
        monkeypatch,
        data,
        signal_idx=signal_idx,
        close_signal=112.0,
        canal_upper_signal=110.0,
        canal_lower_signal=101.0,
        bbmc_signal=100.0,
        ssl_upper_signal=100.5,
        ssl_lower_signal=98.0,
        signal_canal_green=False,
        flip_direction="down",
        flip_gap=6,
        flip_avg=105.0,
    )

    v2 = HMASSLOsciV2().generate_signals(data.copy(), params)

    assert v2["long_entries"].iloc[signal_idx]
    assert v2["sl_long"].iloc[signal_idx] == 105.0
