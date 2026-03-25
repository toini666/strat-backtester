import math
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pandas_ta_classic as ta

from src.strategies.hma_ssl_osci import HMASSLOsci


def _manual_wma(series: pd.Series, length: int) -> pd.Series:
    weights = np.arange(1, length + 1, dtype=float)
    total_weight = weights.sum()
    return series.rolling(length).apply(
        lambda values: float(np.dot(values, weights) / total_weight),
        raw=True,
    )


def _manual_hma(
    series: pd.Series,
    length: int,
    *,
    use_rounded_half: bool,
    use_rounded_sqrt: bool,
) -> pd.Series:
    half_length = int(length / 2 + 0.5) if use_rounded_half else int(length / 2)
    sqrt_length = int(round(math.sqrt(length))) if use_rounded_sqrt else int(math.sqrt(length))
    wmaf = _manual_wma(series, half_length)
    wmas = _manual_wma(series, length)
    return _manual_wma(2 * wmaf - wmas, sqrt_length)


def test_hma_matches_pine_ta_hma_floor_half_and_floor_sqrt():
    close = pd.Series(np.linspace(100.0, 140.0, 64))

    actual = ta.hma(close, length=13)
    expected = _manual_hma(
        close,
        13,
        use_rounded_half=False,
        use_rounded_sqrt=False,
    )
    legacy_half = _manual_hma(
        close,
        13,
        use_rounded_half=True,
        use_rounded_sqrt=False,
    )
    legacy_sqrt = _manual_hma(
        close,
        13,
        use_rounded_half=False,
        use_rounded_sqrt=True,
    )

    pd.testing.assert_series_equal(
        actual.dropna().reset_index(drop=True),
        expected.dropna().reset_index(drop=True),
        check_names=False,
    )
    assert not math.isclose(
        float(actual.dropna().iloc[-1]),
        float(legacy_half.dropna().iloc[-1]),
        rel_tol=0.0,
        abs_tol=1e-9,
    )
    assert not math.isclose(
        float(actual.dropna().iloc[-1]),
        float(legacy_sqrt.dropna().iloc[-1]),
        rel_tol=0.0,
        abs_tol=1e-9,
    )


def test_hma_ssl_baseline_uses_rounded_sqrt_variant():
    close = pd.Series(np.linspace(100.0, 140.0, 96))

    actual = HMASSLOsci._hma_with_rounded_sqrt(close, 60)
    expected = _manual_hma(
        close,
        60,
        use_rounded_half=False,
        use_rounded_sqrt=True,
    )
    ta_hma = ta.hma(close, length=60)

    pd.testing.assert_series_equal(
        actual.dropna().reset_index(drop=True),
        expected.dropna().reset_index(drop=True),
        check_names=False,
    )
    assert not math.isclose(
        float(actual.dropna().iloc[-1]),
        float(ta_hma.dropna().iloc[-1]),
        rel_tol=0.0,
        abs_tol=1e-9,
    )


def test_hma_ssl_osci_debug_frame_records_effective_hma_params():
    index = pd.date_range("2024-01-01", periods=320, freq="7min", tz="Europe/Brussels")
    base = np.linspace(100.0, 125.0, len(index))
    wiggle = np.sin(np.arange(len(index)) / 7.0)
    close = base + wiggle

    data = pd.DataFrame(
        {
            "Open": close - 0.2,
            "High": close + 0.4,
            "Low": close - 0.4,
            "Close": close,
            "Volume": np.full(len(index), 1000.0),
        },
        index=index,
    )

    strategy = HMASSLOsci()
    params = strategy.default_params.copy()
    params.update(
        {
            "ema_len": 13,
            "hma1_len": 13,
            "hma2_len": 21,
            "amp_mult": 2.0,
            "ssl_len": 60,
            "ssl_mult": 0.2,
            "tick_size": 0.25,
        }
    )

    debug_frame = strategy.generate_signals(data, params)["debug_frame"]

    assert set(debug_frame["param_ema_len"].unique()) == {13}
    assert set(debug_frame["param_hma1_len"].unique()) == {13}
    assert set(debug_frame["param_hma2_len"].unique()) == {21}
    assert set(debug_frame["param_amp_mult"].unique()) == {2.0}
    assert set(debug_frame["param_ssl_len"].unique()) == {60}
    assert set(debug_frame["param_ssl_mult"].unique()) == {0.2}
