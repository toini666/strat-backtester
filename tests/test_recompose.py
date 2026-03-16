import pandas as pd

from src.data.market_store import MarketDataStore, SYMBOL_CONTRACTS
from src.data.recompose import recompose_bars


def _make_1m_frame(index: pd.DatetimeIndex) -> pd.DataFrame:
    base = pd.Series(range(len(index)), index=index, dtype=float)
    return pd.DataFrame(
        {
            "Open": 100.0 + base,
            "High": 100.5 + base,
            "Low": 99.5 + base,
            "Close": 100.25 + base,
            "Volume": 1000,
        },
        index=index,
    )


def test_recompose_resets_anchor_after_market_gap():
    first_session = pd.date_range("2026-03-11 23:00:00+01:00", periods=14, freq="1min")
    second_session = pd.date_range("2026-03-12 23:00:00+01:00", periods=14, freq="1min")
    df = _make_1m_frame(first_session.append(second_session))

    recomposed = recompose_bars(df, "7m")

    assert list(recomposed.index.astype(str)) == [
        "2026-03-11 23:00:00+01:00",
        "2026-03-11 23:07:00+01:00",
        "2026-03-12 23:00:00+01:00",
        "2026-03-12 23:07:00+01:00",
    ]


def test_recompose_keeps_partial_last_bar_before_daily_gap():
    first_session = pd.date_range("2026-03-11 21:49:00+01:00", periods=11, freq="1min")
    second_session = pd.date_range("2026-03-11 23:00:00+01:00", periods=7, freq="1min")
    df = _make_1m_frame(first_session.append(second_session))

    recomposed = recompose_bars(df, "7m")

    assert list(recomposed.index.astype(str)) == [
        "2026-03-11 21:49:00+01:00",
        "2026-03-11 21:56:00+01:00",
        "2026-03-11 23:00:00+01:00",
    ]
    assert recomposed.loc[pd.Timestamp("2026-03-11 21:56:00+01:00"), "Close"] == df.iloc[10]["Close"]
    assert recomposed.loc[pd.Timestamp("2026-03-11 23:00:00+01:00"), "Close"] == df.iloc[-1]["Close"]


def test_market_store_load_bars_keeps_session_anchor_when_slicing_mid_session(tmp_path):
    symbol = "MNQ"
    contract_id = SYMBOL_CONTRACTS[symbol]
    store = MarketDataStore(data_dir=tmp_path)

    session = pd.date_range("2026-03-11 23:00:00+01:00", periods=14, freq="1min")
    df = _make_1m_frame(session)

    symbol_dir = tmp_path / symbol
    symbol_dir.mkdir(parents=True, exist_ok=True)
    df.to_csv(symbol_dir / f"{symbol}_1m.csv", index_label="Date")

    store._save_index(
        [
            {
                "id": "dataset-1",
                "symbol": symbol,
                "contract_id": contract_id,
                "start_date": str(df.index.min()),
                "end_date": str(df.index.max()),
                "bar_count_1m": len(df),
                "total_size_mb": 0.01,
                "timeframes": ["1m", "7m"],
                "timezone": "Europe/Brussels",
                "updated_at": "2026-03-15T09:00:00",
            }
        ]
    )

    loaded = store.load_bars(
        contract_id=contract_id,
        start=pd.Timestamp("2026-03-11 23:05:00+01:00"),
        end=pd.Timestamp("2026-03-11 23:20:00+01:00"),
        timeframe="7m",
    )

    assert list(loaded.index.astype(str)) == ["2026-03-11 23:07:00+01:00"]
