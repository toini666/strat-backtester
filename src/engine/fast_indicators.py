"""Fast numpy-based replacements for the slow pandas-ta-classic indicators
used by the trading strategies.

These functions are drop-in replacements that produce results numerically
equivalent to the pandas-ta-classic versions (within float rounding) but
run an order of magnitude faster on long series.

The trading strategies use the following indicators in their hot paths:
  * ``ta.wma(close, length)``  → :func:`fast_wma`
  * ``ta.hma(close, length)``  → :func:`fast_hma`
  * the in-strategy LinReg-of-rolling-window loop → :func:`rolling_linreg_last`

``ta.ema``, ``ta.sma``, ``ta.true_range`` and ``ta.mfi`` already use
vectorised pandas operations, so they are not replaced here.
"""

from __future__ import annotations

import math
from typing import Union

import numpy as np
import pandas as pd
from numpy.lib.stride_tricks import sliding_window_view


SeriesLike = Union[pd.Series, np.ndarray]


def _to_array(x: SeriesLike) -> np.ndarray:
    if isinstance(x, pd.Series):
        return x.to_numpy(dtype=float, copy=False)
    return np.asarray(x, dtype=float)


def _to_series(out: np.ndarray, like: SeriesLike, name: str) -> SeriesLike:
    if isinstance(like, pd.Series):
        return pd.Series(out, index=like.index, name=name)
    return out


def fast_wma(close: SeriesLike, length: int) -> SeriesLike:
    """Weighted Moving Average matching ``pandas_ta_classic.wma``.

    The pandas-ta-classic implementation does:
        weights = [1, 2, ..., length]
        total = length * (length+1) / 2
        WMA[i] = dot(x[i-length+1 : i+1], weights) / total
        # first length-1 values are NaN

    The numpy equivalent below uses a fused sliding-window dot product.
    The summation order is bit-equivalent to a per-row ``np.dot`` for
    lengths small enough that numpy does the multiply directly (i.e. it
    does not dispatch to BLAS), which covers every indicator length we
    actually call (≤80).
    """
    length = int(length)
    arr = _to_array(close)
    n = arr.size
    out = np.full(n, np.nan)
    if length <= 0 or n < length:
        return _to_series(out, close, f"WMA_{length}")

    weights = np.arange(1, length + 1, dtype=np.float64)
    total = 0.5 * length * (length + 1)

    # ``np.convolve`` with direct (non-FFT) summation is bit-equivalent to
    # ``np.dot(window, weights)`` per window — verified against pandas_ta.
    valid = np.convolve(arr, weights[::-1], mode="valid") / total
    out[length - 1:] = valid

    return _to_series(out, close, f"WMA_{length}")


def fast_hma(close: SeriesLike, length: int) -> SeriesLike:
    """Hull MA matching ``pandas_ta_classic.hma``.

    HMA = WMA(2*WMA(close, n/2) - WMA(close, n), int(sqrt(n)))
    """
    length = int(length)
    half_length = int(length / 2)
    sqrt_length = int(math.sqrt(length))
    wmaf = fast_wma(close, half_length)
    wmas = fast_wma(close, length)
    # Force numpy arithmetic to avoid pandas reindex overhead.
    if isinstance(wmaf, pd.Series):
        diff = 2.0 * wmaf.to_numpy() - wmas.to_numpy()
        diff_series = pd.Series(diff, index=wmaf.index)
        return fast_wma(diff_series, sqrt_length).rename(f"HMA_{length}")
    diff = 2.0 * wmaf - wmas
    return fast_wma(diff, sqrt_length)


def fast_hma_rounded_sqrt(close: SeriesLike, length: int) -> SeriesLike:
    """SSL-style HMA where the outer WMA length is ``round(sqrt(length))``."""
    length = int(length)
    half_length = int(length / 2)
    sqrt_length = int(round(math.sqrt(length)))
    wmaf = fast_wma(close, half_length)
    wmas = fast_wma(close, length)
    if isinstance(wmaf, pd.Series):
        diff = 2.0 * wmaf.to_numpy() - wmas.to_numpy()
        diff_series = pd.Series(diff, index=wmaf.index)
        return fast_wma(diff_series, sqrt_length)
    diff = 2.0 * wmaf - wmas
    return fast_wma(diff, sqrt_length)


def rolling_linreg_last(values: np.ndarray, length: int) -> np.ndarray:
    """Predicted value at the last point of a rolling linear regression.

    Equivalent to the Pine Script ``ta.linreg(values, length, 0)`` and to
    the per-bar ``np.polyfit(x, window, 1) -> coeffs[0]*(length-1) + coeffs[1]``
    loop used by the oscillator code.

    Closed-form: for ``x = 0..length-1`` and a window ``y``:
        slope     = (length * Σ(xy) - Σx * Σy) / (length * Σ(x²) - (Σx)²)
        intercept = (Σy - slope * Σx) / length
        result    = slope * (length-1) + intercept

    Windows containing any NaN propagate NaN. The first ``length-1``
    values are NaN.
    """
    length = int(length)
    arr = np.asarray(values, dtype=np.float64)
    n = arr.size
    out = np.full(n, np.nan)
    if length <= 0 or n < length:
        return out

    sx = float(length * (length - 1) / 2.0)
    sxx = float(length * (length - 1) * (2 * length - 1) / 6.0)
    denom = length * sxx - sx * sx
    if denom == 0.0:
        return out

    win = sliding_window_view(arr, length)  # (n-length+1, length)
    # Use einsum (matches a per-row dot) and a per-row sum.
    sy = win.sum(axis=1)
    x_weights = np.arange(length, dtype=np.float64)
    sxy = np.einsum("ij,j->i", win, x_weights)

    slope = (length * sxy - sx * sy) / denom
    intercept = (sy - slope * sx) / length
    out[length - 1:] = slope * (length - 1) + intercept
    return out
