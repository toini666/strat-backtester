"""
Timeframe recomposition module.

Builds higher-timeframe OHLCV bars from 1-minute base data.
"""
from __future__ import annotations

import pandas as pd


# Map user-facing timeframe strings to pandas Grouper frequencies
TIMEFRAME_FREQ_MAP = {
    "1m": "1min",
    "2m": "2min",
    "3m": "3min",
    "5m": "5min",
    "7m": "7min",
    "15m": "15min",
    "30m": "30min",
    "1h": "1h",
    "4h": "4h",
    "1d": "1D",
}

# Expected number of 1m bars per resampled bar
_MINUTES_PER_TF = {
    "2m": 2,
    "3m": 3,
    "5m": 5,
    "7m": 7,
    "15m": 15,
    "30m": 30,
    "1h": 60,
    "4h": 240,
}

# Futures sessions restart after the daily market break. We only reset the
# resampling anchor on large gaps, not on small missing-data glitches.
SESSION_GAP_THRESHOLD = pd.Timedelta(minutes=30)
SESSION_CLOSE_HOURS = {21, 22}


def _ends_on_session_close(ts: pd.Timestamp) -> bool:
    if ts.tzinfo is None:
        ts = ts.tz_localize("UTC")
    local_ts = ts.tz_convert("Europe/Brussels")
    return local_ts.minute == 59 and local_ts.hour in SESSION_CLOSE_HOURS


def _iter_session_segments(df_1m: pd.DataFrame) -> list[tuple[pd.DataFrame, bool]]:
    if df_1m.empty:
        return []

    diffs = df_1m.index.to_series().diff()
    session_ids = (diffs > SESSION_GAP_THRESHOLD).cumsum()
    grouped_segments = [segment for _, segment in df_1m.groupby(session_ids) if not segment.empty]

    segments: list[tuple[pd.DataFrame, bool]] = []
    for idx, segment in enumerate(grouped_segments):
        has_next_session = idx < (len(grouped_segments) - 1)
        keep_partial_last_bar = has_next_session or _ends_on_session_close(segment.index[-1])
        segments.append((segment, keep_partial_last_bar))
    return segments


def _resample_segment(
    segment: pd.DataFrame,
    freq: str,
    expected: int | None,
    keep_partial_last_bar: bool,
) -> pd.DataFrame:
    origin = segment.index[0]
    resampled = segment.resample(
        freq,
        origin=origin,
        label="left",
        closed="left",
    ).agg(
        {
            "Open": "first",
            "High": "max",
            "Low": "min",
            "Close": "last",
            "Volume": "sum",
        }
    )
    resampled.dropna(subset=["Open"], inplace=True)

    if expected is None or resampled.empty:
        return resampled

    bar_counts = segment.resample(
        freq,
        origin=origin,
        label="left",
        closed="left",
    )["Close"].count()

    valid_index = bar_counts[bar_counts >= expected].index
    if keep_partial_last_bar and not bar_counts.empty and bar_counts.iloc[-1] > 0:
        valid_index = valid_index.union(pd.DatetimeIndex([bar_counts.index[-1]]))
    return resampled.loc[resampled.index.intersection(valid_index)]


def recompose_bars(df_1m: pd.DataFrame, target_timeframe: str) -> pd.DataFrame:
    """
    Recompose higher-timeframe bars from 1-minute OHLCV data.

    Incomplete bars at the start of each trading session are removed.
    The last bar before the daily market break is preserved even if it is a
    partial timeframe bar, so indicator state matches the source session close.
    A session restarts after the market closure gap, so 7m/15m bars realign
    from the first 1-minute bar available after the reopen.

    Args:
        df_1m: DataFrame with DatetimeIndex and columns [Open, High, Low, Close, Volume].
               Must be sorted chronologically (ascending).
        target_timeframe: Target timeframe string (e.g. '5m', '15m', '1h').

    Returns:
        DataFrame with the same OHLCV columns resampled to the target timeframe.
    """
    if target_timeframe == "1m":
        return df_1m.copy()

    freq = TIMEFRAME_FREQ_MAP.get(target_timeframe)
    if freq is None:
        raise ValueError(
            f"Unsupported timeframe '{target_timeframe}'. "
            f"Supported: {list(TIMEFRAME_FREQ_MAP.keys())}"
        )

    if df_1m.empty:
        return df_1m.copy()

    expected = _MINUTES_PER_TF.get(target_timeframe)
    segments = _iter_session_segments(df_1m.sort_index())

    recomposed_segments = [
        _resample_segment(segment, freq, expected, keep_partial_last_bar)
        for segment, keep_partial_last_bar in segments
    ]
    recomposed_segments = [segment for segment in recomposed_segments if not segment.empty]

    if not recomposed_segments:
        return df_1m.iloc[0:0].copy()

    return pd.concat(recomposed_segments).sort_index()
