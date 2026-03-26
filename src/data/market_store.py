"""
Persistent market data store.

Manages local storage of 1-minute OHLCV bars as CSV files,
organized by asset symbol with Europe/Brussels timezone.
Recomposed timeframes (2m, 3m, 5m, 7m, 15m) are generated from 1m base data.
"""
import json
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

from .recompose import recompose_bars

logger = logging.getLogger(__name__)

# Project-relative storage directory
DATA_DIR = Path(__file__).parent.parent.parent / "data" / "market_data"

BRUSSELS_TZ = "Europe/Brussels"

# Map symbol short names to current active contract IDs
# Updated as contracts roll over
SYMBOL_CONTRACTS = {
    "MNQ": "CON.F.US.MNQ.M26",
    "MES": "CON.F.US.MES.M26",
    "MYM": "CON.F.US.MYM.M26",
    "MGC": "CON.F.US.MGC.J26",
    "MBT": "CON.F.US.MBT.J26",
    "M2K": "CON.F.US.M2K.M26",
    "MCL": "CON.F.US.MCLE.K26",
}

# Timeframes to generate from 1m data
RECOMPOSE_TIMEFRAMES = ["2m", "3m", "5m", "7m", "15m"]


def _to_brussels(df: pd.DataFrame) -> pd.DataFrame:
    """Convert DataFrame index to Europe/Brussels timezone."""
    if df.index.tz is None:
        df.index = df.index.tz_localize("UTC")
    df.index = df.index.tz_convert(BRUSSELS_TZ)
    return df


class MarketDataStore:
    """
    Manages persistent storage of market bar data.

    Structure:
        data/market_data/
            index.json
            MNQ/
                MNQ_1m.csv
                MNQ_2m.csv
                MNQ_5m.csv
                ...
            MES/
                MES_1m.csv
                ...
    """

    def __init__(self, data_dir: Optional[Path] = None):
        self.data_dir = data_dir or DATA_DIR
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.index_path = self.data_dir / "index.json"

    # ---- Index management ----

    def _load_index(self) -> List[Dict[str, Any]]:
        if not self.index_path.exists():
            return []
        try:
            with open(self.index_path, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            logger.warning("Corrupted index.json, returning empty index")
            return []

    def _save_index(self, index: List[Dict[str, Any]]) -> None:
        with open(self.index_path, "w") as f:
            json.dump(index, f, indent=2, default=str)

    def _get_symbol_dir(self, symbol: str) -> Path:
        """Get or create the subdirectory for a symbol."""
        symbol_dir = self.data_dir / symbol
        symbol_dir.mkdir(parents=True, exist_ok=True)
        return symbol_dir

    # ---- Public API ----

    def list_datasets(self) -> List[Dict[str, Any]]:
        return self._load_index()

    def get_dataset(self, contract_id: str) -> Optional[Dict[str, Any]]:
        """Get metadata for a specific contract's dataset."""
        for ds in self._load_index():
            if ds["contract_id"] == contract_id:
                return ds
        return None

    def get_dataset_by_symbol(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get metadata for a specific symbol's dataset."""
        for ds in self._load_index():
            if ds.get("symbol") == symbol:
                return ds
        return None

    def has_coverage(self, contract_id: str, start: datetime, end: datetime) -> bool:
        """Check if local 1-min data fully covers the requested date range."""
        # Try by contract_id first, then by symbol
        ds = self.get_dataset(contract_id)
        if ds is None:
            # Extract symbol from contract_id (e.g., CON.F.US.MNQ.H26 -> MNQ)
            for symbol, cid in SYMBOL_CONTRACTS.items():
                if cid == contract_id:
                    ds = self.get_dataset_by_symbol(symbol)
                    break
        if ds is None:
            return False

        ds_start = pd.Timestamp(ds["start_date"])
        ds_end = pd.Timestamp(ds["end_date"])
        req_start = pd.Timestamp(start)
        req_end = pd.Timestamp(end)

        # Normalize to naive for comparison
        ds_start_n = ds_start.tz_localize(None) if ds_start.tzinfo else ds_start
        ds_end_n = ds_end.tz_localize(None) if ds_end.tzinfo else ds_end
        req_start_n = req_start.tz_localize(None) if req_start.tzinfo else req_start
        req_end_n = req_end.tz_localize(None) if req_end.tzinfo else req_end

        return ds_start_n <= req_start_n and ds_end_n >= req_end_n

    def load_bars(
        self,
        contract_id: str,
        start: datetime,
        end: datetime,
        timeframe: str = "1m",
    ) -> pd.DataFrame:
        """Load bars from local store, recomposing to the requested timeframe."""
        # Resolve symbol
        symbol = None
        for sym, cid in SYMBOL_CONTRACTS.items():
            if cid == contract_id:
                symbol = sym
                break

        ds = self.get_dataset(contract_id)
        if ds is None and symbol:
            ds = self.get_dataset_by_symbol(symbol)
        if ds is None:
            raise FileNotFoundError(f"No local data for contract {contract_id}")

        sym = ds.get("symbol", symbol or "unknown")
        csv_path = self._get_symbol_dir(sym) / f"{sym}_1m.csv"
        if not csv_path.exists():
            raise FileNotFoundError(f"CSV file missing: {csv_path}")

        slice_start = pd.Timestamp(start)
        slice_end = pd.Timestamp(end)

        if slice_start.tzinfo is None:
            slice_start = slice_start.tz_localize("UTC")
        if slice_end.tzinfo is None:
            slice_end = slice_end.tz_localize("UTC")
        slice_start = slice_start.tz_convert(BRUSSELS_TZ)
        slice_end = slice_end.tz_convert(BRUSSELS_TZ)

        # Use pre-computed CSV if available, otherwise recompose from 1m
        tf_csv_path = self._get_symbol_dir(sym) / f"{sym}_{timeframe}.csv"
        if timeframe != "1m" and tf_csv_path.exists():
            logger.info(f"Loading local data for {sym} from {tf_csv_path}")
            df = pd.read_csv(tf_csv_path, index_col="Date")
            df.index = pd.to_datetime(df.index, utc=True)
            df.index = df.index.tz_convert(BRUSSELS_TZ)
            df = df[(df.index >= slice_start) & (df.index <= slice_end)]
            logger.info(f"Loaded {len(df)} {timeframe} bars from local store")
        else:
            logger.info(f"Loading local data for {sym} from {csv_path}")
            df = pd.read_csv(csv_path, index_col="Date")
            df.index = pd.to_datetime(df.index, utc=True)
            df.index = df.index.tz_convert(BRUSSELS_TZ)
            if timeframe != "1m":
                df = recompose_bars(df, timeframe)
                df = df[(df.index >= slice_start) & (df.index <= slice_end)]
                logger.info(f"Recomposed {len(df)} bars at {timeframe} from local 1m data")
            else:
                df = df[(df.index >= slice_start) & (df.index <= slice_end)]
                logger.info(f"Loaded {len(df)} 1m bars from local store")

        return df

    def save_bars(
        self,
        symbol: str,
        contract_id: str,
        df: pd.DataFrame,
    ) -> Dict[str, Any]:
        """
        Save 1-minute bars and generate all recomposed timeframes.

        Merges with existing data if present.
        Converts to Europe/Brussels timezone.
        Saves as CSV files in symbol subdirectory.

        Returns:
            Updated dataset metadata dict.
        """
        symbol_dir = self._get_symbol_dir(symbol)
        csv_1m_path = symbol_dir / f"{symbol}_1m.csv"

        # Convert to Brussels timezone
        df = _to_brussels(df)

        # Merge with existing data if present
        if csv_1m_path.exists():
            logger.info(f"Merging with existing data for {symbol}")
            existing = pd.read_csv(csv_1m_path, index_col="Date")
            existing.index = pd.to_datetime(existing.index, utc=True)
            existing.index = existing.index.tz_convert(BRUSSELS_TZ)

            # On contract rolls, keep the existing symbol history authoritative up
            # to its last known bar. The new contract may overlap the same local
            # timestamps (for example when the download starts a day earlier), but
            # those overlapping bars must not overwrite the prior contract's close
            # of session data.
            dataset_entry = None
            for entry in self._load_index():
                if entry.get("symbol") == symbol:
                    dataset_entry = entry
                    break
            if dataset_entry and dataset_entry.get("contract_id") != contract_id:
                existing_end = pd.Timestamp(dataset_entry["end_date"])
                if existing_end.tzinfo is None:
                    existing_end = existing_end.tz_localize(BRUSSELS_TZ)
                else:
                    existing_end = existing_end.tz_convert(BRUSSELS_TZ)
                df = df[df.index > existing_end]

            df = pd.concat([existing, df])
            df = df[~df.index.duplicated(keep="last")]
            df.sort_index(ascending=True, inplace=True)

        # Save 1m CSV
        df.to_csv(csv_1m_path, index_label="Date")
        logger.info(f"Saved {len(df)} 1m bars to {csv_1m_path}")

        # Generate all recomposed timeframes
        for tf in RECOMPOSE_TIMEFRAMES:
            df_recomposed = recompose_bars(df, tf)
            csv_path = symbol_dir / f"{symbol}_{tf}.csv"
            df_recomposed.to_csv(csv_path, index_label="Date")
            logger.info(f"Generated {symbol}_{tf}.csv: {len(df_recomposed)} bars")

        # Calculate file size (all CSVs combined)
        total_size = sum(f.stat().st_size for f in symbol_dir.glob("*.csv"))
        total_size_mb = round(total_size / (1024 * 1024), 2)

        # Update index
        index = self._load_index()
        dataset_entry = None
        for entry in index:
            if entry.get("symbol") == symbol:
                dataset_entry = entry
                break

        # Maintain contract segments history
        existing_segments = dataset_entry.get("contract_segments", []) if dataset_entry else []
        if not existing_segments and dataset_entry:
            # Reconstruct initial segment from stored metadata
            old_cid = dataset_entry["contract_id"]
            existing_segments = [{
                "contract": old_cid,
                "label": old_cid.split(".")[-1],
                "from": str(pd.Timestamp(dataset_entry["start_date"]).date()),
                "to": str(pd.Timestamp(dataset_entry["end_date"]).date()),
            }]

        if not existing_segments:
            new_segments = [{
                "contract": contract_id,
                "label": contract_id.split(".")[-1],
                "from": str(df.index.min().date()),
                "to": str(df.index.max().date()),
            }]
        elif existing_segments[-1]["contract"] == contract_id:
            existing_segments[-1]["to"] = str(df.index.max().date())
            new_segments = existing_segments
        else:
            # New contract: close previous segment at old end date, open new one
            old_end = pd.Timestamp(dataset_entry["end_date"]).date() if dataset_entry else df.index.min().date()
            existing_segments[-1]["to"] = str(old_end)
            existing_segments.append({
                "contract": contract_id,
                "label": contract_id.split(".")[-1],
                "from": str(old_end),
                "to": str(df.index.max().date()),
            })
            new_segments = existing_segments

        metadata = {
            "id": dataset_entry["id"] if dataset_entry else str(uuid.uuid4()),
            "symbol": symbol,
            "contract_id": contract_id,
            "start_date": str(df.index.min()),
            "end_date": str(df.index.max()),
            "bar_count_1m": len(df),
            "total_size_mb": total_size_mb,
            "timeframes": ["1m"] + RECOMPOSE_TIMEFRAMES,
            "timezone": BRUSSELS_TZ,
            "updated_at": datetime.utcnow().isoformat(),
            "contract_segments": new_segments,
        }

        if dataset_entry:
            idx = index.index(dataset_entry)
            index[idx] = metadata
        else:
            index.append(metadata)

        self._save_index(index)
        logger.info(
            f"Saved {symbol} data: {len(df)} 1m bars "
            f"({df.index.min()} to {df.index.max()}, {total_size_mb} MB total)"
        )
        return metadata

    def rebuild_recomposed_data(self, symbols: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        Rebuild all derived timeframe CSVs from the stored 1-minute source files.

        This is used when the recomposition logic changes and existing on-disk
        timeframe files need to be regenerated without downloading new market data.
        """
        index = self._load_index()
        target_symbols = set(symbols) if symbols else None
        rebuilt: List[Dict[str, Any]] = []

        for entry in index:
            symbol = entry.get("symbol")
            if not symbol:
                continue
            if target_symbols is not None and symbol not in target_symbols:
                continue

            csv_1m_path = self._get_symbol_dir(symbol) / f"{symbol}_1m.csv"
            if not csv_1m_path.exists():
                logger.warning("Skipping %s: missing %s", symbol, csv_1m_path)
                continue

            df_1m = pd.read_csv(csv_1m_path, index_col="Date")
            df_1m.index = pd.to_datetime(df_1m.index, utc=True)
            df_1m.index = df_1m.index.tz_convert(BRUSSELS_TZ)
            df_1m.sort_index(inplace=True)

            for tf in RECOMPOSE_TIMEFRAMES:
                df_recomposed = recompose_bars(df_1m, tf)
                csv_path = self._get_symbol_dir(symbol) / f"{symbol}_{tf}.csv"
                df_recomposed.to_csv(csv_path, index_label="Date")
                logger.info("Rebuilt %s_%s.csv: %s bars", symbol, tf, len(df_recomposed))

            total_size = sum(f.stat().st_size for f in self._get_symbol_dir(symbol).glob("*.csv"))
            entry["start_date"] = str(df_1m.index.min())
            entry["end_date"] = str(df_1m.index.max())
            entry["bar_count_1m"] = len(df_1m)
            entry["total_size_mb"] = round(total_size / (1024 * 1024), 2)
            entry["timeframes"] = ["1m"] + RECOMPOSE_TIMEFRAMES
            entry["timezone"] = BRUSSELS_TZ
            entry["updated_at"] = datetime.utcnow().isoformat()
            rebuilt.append(entry.copy())

        self._save_index(index)
        return rebuilt

    def delete_dataset(self, dataset_id: str) -> bool:
        """Remove a dataset by its ID."""
        index = self._load_index()
        entry = None
        for ds in index:
            if ds["id"] == dataset_id:
                entry = ds
                break

        if entry is None:
            return False

        # Remove symbol directory
        symbol = entry.get("symbol")
        if symbol:
            symbol_dir = self.data_dir / symbol
            if symbol_dir.exists():
                import shutil
                shutil.rmtree(symbol_dir)
                logger.info(f"Deleted directory: {symbol_dir}")

        index.remove(entry)
        self._save_index(index)
        logger.info(f"Deleted dataset {dataset_id} ({symbol})")
        return True
