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


def test_market_store_save_bars_does_not_overwrite_existing_rows_on_contract_roll(tmp_path):
    symbol = "MNQ"
    old_contract = "CON.F.US.MNQ.H26"
    new_contract = "CON.F.US.MNQ.M26"
    store = MarketDataStore(data_dir=tmp_path)

    existing_index = pd.DatetimeIndex(
        [
            "2026-03-16 21:58:00+01:00",
            "2026-03-16 21:59:00+01:00",
        ]
    )
    existing = pd.DataFrame(
        {
            "Open": [100.0, 101.0],
            "High": [100.5, 101.5],
            "Low": [99.5, 100.5],
            "Close": [100.25, 101.25],
            "Volume": [10, 20],
        },
        index=existing_index,
    )

    symbol_dir = tmp_path / symbol
    symbol_dir.mkdir(parents=True, exist_ok=True)
    existing.to_csv(symbol_dir / f"{symbol}_1m.csv", index_label="Date")

    store._save_index(
        [
            {
                "id": "dataset-1",
                "symbol": symbol,
                "contract_id": old_contract,
                "start_date": str(existing.index.min()),
                "end_date": str(existing.index.max()),
                "bar_count_1m": len(existing),
                "total_size_mb": 0.01,
                "timeframes": ["1m", "7m"],
                "timezone": "Europe/Brussels",
                "updated_at": "2026-03-16T22:00:00",
                "contract_segments": [
                    {
                        "contract": old_contract,
                        "label": "H26",
                        "from": "2026-01-15",
                        "to": "2026-03-16",
                    }
                ],
            }
        ]
    )

    new_index = pd.DatetimeIndex(
        [
            "2026-03-16 21:58:00+01:00",
            "2026-03-16 21:59:00+01:00",
            "2026-03-16 23:00:00+01:00",
        ]
    )
    new_contract_data = pd.DataFrame(
        {
            "Open": [200.0, 201.0, 202.0],
            "High": [200.5, 201.5, 202.5],
            "Low": [199.5, 200.5, 201.5],
            "Close": [200.25, 201.25, 202.25],
            "Volume": [30, 40, 50],
        },
        index=new_index,
    )

    metadata = store.save_bars(symbol, new_contract, new_contract_data)

    saved = pd.read_csv(symbol_dir / f"{symbol}_1m.csv", index_col="Date")
    saved.index = pd.to_datetime(saved.index, utc=True).tz_convert("Europe/Brussels")

    assert saved.loc[pd.Timestamp("2026-03-16 21:58:00+01:00"), "Close"] == 100.25
    assert saved.loc[pd.Timestamp("2026-03-16 21:59:00+01:00"), "Close"] == 101.25
    assert saved.loc[pd.Timestamp("2026-03-16 23:00:00+01:00"), "Close"] == 202.25
    assert metadata["contract_id"] == new_contract
    assert metadata["contract_segments"][-1]["contract"] == new_contract
