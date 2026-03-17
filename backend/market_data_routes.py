"""
API routes for managing the local market data store.

Provides endpoints to list, download, and delete locally cached
1-minute bar datasets.
"""
import logging
import threading
import time
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

import pandas as pd
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from src.data.market_store import BRUSSELS_TZ, MarketDataStore, SYMBOL_CONTRACTS, get_next_rollover
from src.data.topstep import TopstepClient

logger = logging.getLogger(__name__)

market_data_router = APIRouter(prefix="/market-data", tags=["Market Data"])

store = MarketDataStore()

ACTIVE_DOWNLOADS: Dict[str, Dict[str, Any]] = {}
_downloads_lock = threading.Lock()
RETENTION_WINDOW_DAYS = 60.0
RETENTION_WARNING_DAYS = 7.0


class DownloadRequest(BaseModel):
    contract_id: str = Field(..., min_length=1, description="Topstep contract ID")
    start_date: str = Field(..., description="Start date (YYYY-MM-DD)")
    end_date: str = Field(..., description="End date (YYYY-MM-DD)")


class DownloadStatusResponse(BaseModel):
    download_id: str
    status: str
    progress: float = 0.0
    bars_downloaded: int = 0
    message: str = ""


class RolloverInfo(BaseModel):
    from_contract: str
    to_contract: str
    date: str
    next_contract_id: str


class ContractSegment(BaseModel):
    contract: str
    label: str
    from_date: str = Field(..., alias="from")
    to_date: str = Field(..., alias="to")

    class Config:
        populate_by_name = True


class MarketDatasetResponse(BaseModel):
    id: str
    symbol: str
    contract_id: str
    start_date: str
    end_date: str
    bar_count_1m: int
    total_size_mb: float
    timeframes: List[str] = Field(default_factory=list)
    timezone: str
    updated_at: str
    missing_hours: float
    missing_days: float
    days_until_retention_limit: float
    retention_warning: bool
    retention_exceeded: bool
    next_rollover: Optional[RolloverInfo] = None
    contract_segments: List[ContractSegment] = Field(default_factory=list)


def _resolve_symbol(contract_id: str) -> str:
    for symbol, current_contract_id in SYMBOL_CONTRACTS.items():
        if current_contract_id == contract_id:
            return symbol
    raise HTTPException(status_code=400, detail=f"Unknown contract_id: {contract_id}")


def _to_brussels_timestamp(value: Any) -> pd.Timestamp:
    ts = pd.Timestamp(value)
    if ts.tzinfo is None:
        return ts.tz_localize(BRUSSELS_TZ)
    return ts.tz_convert(BRUSSELS_TZ)


def _extract_contract_label(contract_id: str) -> str:
    """Extract short label from contract ID (e.g. 'CON.F.US.MNQ.M26' → 'M26')."""
    parts = contract_id.split(".")
    return parts[-1] if parts else contract_id


def _build_contract_segments(dataset: Dict[str, Any]) -> List[ContractSegment]:
    """Build contract segments list, generating a fallback if none stored."""
    raw = dataset.get("contract_segments", [])
    if raw:
        return [ContractSegment(**seg) for seg in raw]

    # Fallback: create a single segment from the dataset's contract_id
    contract_id = dataset.get("contract_id", "")
    label = _extract_contract_label(contract_id)
    start = str(_to_brussels_timestamp(dataset["start_date"]).date()) if dataset.get("start_date") else ""
    end = str(_to_brussels_timestamp(dataset["end_date"]).date()) if dataset.get("end_date") else ""
    return [ContractSegment(contract=contract_id, label=label, **{"from": start, "to": end})]


def _serialize_dataset(dataset: Dict[str, Any]) -> MarketDatasetResponse:
    now = pd.Timestamp.now(tz=BRUSSELS_TZ)
    end_ts = _to_brussels_timestamp(dataset["end_date"])
    missing_hours = max(0.0, (now - end_ts).total_seconds() / 3600.0)
    missing_days = missing_hours / 24.0
    days_until_retention_limit = RETENTION_WINDOW_DAYS - missing_days

    symbol = dataset.get("symbol", "")
    roll = get_next_rollover(symbol)
    rollover_info = None
    if roll:
        rollover_info = RolloverInfo(
            from_contract=roll["from"],
            to_contract=roll["to"],
            date=roll["date"],
            next_contract_id=roll["next_contract"],
        )

    return MarketDatasetResponse(
        id=dataset["id"],
        symbol=symbol,
        contract_id=dataset["contract_id"],
        start_date=str(_to_brussels_timestamp(dataset["start_date"])),
        end_date=str(end_ts),
        bar_count_1m=int(dataset.get("bar_count_1m", 0)),
        total_size_mb=float(dataset.get("total_size_mb", 0.0)),
        timeframes=list(dataset.get("timeframes", [])),
        timezone=str(dataset.get("timezone", BRUSSELS_TZ)),
        updated_at=str(dataset.get("updated_at", "")),
        missing_hours=round(missing_hours, 2),
        missing_days=round(missing_days, 2),
        days_until_retention_limit=round(days_until_retention_limit, 2),
        retention_warning=0.0 <= days_until_retention_limit <= RETENTION_WARNING_DAYS,
        retention_exceeded=days_until_retention_limit < 0.0,
        next_rollover=rollover_info,
        contract_segments=_build_contract_segments(dataset),
    )


def _run_download(download_id: str, contract_id: str, start: datetime, end: datetime) -> None:
    try:
        with _downloads_lock:
            ACTIVE_DOWNLOADS[download_id]["status"] = "in_progress"
            ACTIVE_DOWNLOADS[download_id]["message"] = "Fetching 1-minute bars from Topstep API..."

        symbol = _resolve_symbol(contract_id)
        client = TopstepClient()
        data = client.fetch_historical_data(
            contract_id=contract_id,
            start=start,
            end=end,
            timeframe="1m",
            live=False,
        )

        if data.empty:
            with _downloads_lock:
                ACTIVE_DOWNLOADS[download_id]["status"] = "failed"
                ACTIVE_DOWNLOADS[download_id]["message"] = "No data returned from API"
                ACTIVE_DOWNLOADS[download_id]["finished_at"] = time.time()
            return

        with _downloads_lock:
            ACTIVE_DOWNLOADS[download_id]["bars_downloaded"] = len(data)
            ACTIVE_DOWNLOADS[download_id]["progress"] = 0.8
            ACTIVE_DOWNLOADS[download_id]["message"] = f"Saving {len(data)} bars to local store..."

        metadata = store.save_bars(symbol=symbol, contract_id=contract_id, df=data)

        with _downloads_lock:
            ACTIVE_DOWNLOADS[download_id]["status"] = "completed"
            ACTIVE_DOWNLOADS[download_id]["progress"] = 1.0
            ACTIVE_DOWNLOADS[download_id]["bars_downloaded"] = metadata["bar_count_1m"]
            ACTIVE_DOWNLOADS[download_id]["message"] = (
                f"Downloaded {metadata['bar_count_1m']} bars "
                f"({metadata['start_date']} to {metadata['end_date']}, "
                f"{metadata['total_size_mb']} MB total)."
            )
            ACTIVE_DOWNLOADS[download_id]["finished_at"] = time.time()

        logger.info("Download %s completed for %s", download_id, contract_id)

    except HTTPException as exc:
        with _downloads_lock:
            ACTIVE_DOWNLOADS[download_id]["status"] = "failed"
            ACTIVE_DOWNLOADS[download_id]["message"] = exc.detail
            ACTIVE_DOWNLOADS[download_id]["finished_at"] = time.time()
    except Exception as exc:
        logger.error("Download %s failed: %s", download_id, exc, exc_info=True)
        with _downloads_lock:
            ACTIVE_DOWNLOADS[download_id]["status"] = "failed"
            ACTIVE_DOWNLOADS[download_id]["message"] = f"Download failed: {exc}"
            ACTIVE_DOWNLOADS[download_id]["finished_at"] = time.time()


def _cleanup_old_downloads() -> None:
    now = time.time()
    with _downloads_lock:
        to_remove = []
        for download_id, info in ACTIVE_DOWNLOADS.items():
            if info["status"] in ("completed", "failed"):
                if now - info.get("finished_at", now) > 600:
                    to_remove.append(download_id)
        for download_id in to_remove:
            del ACTIVE_DOWNLOADS[download_id]


@market_data_router.get("", response_model=List[MarketDatasetResponse])
def list_datasets():
    return [_serialize_dataset(dataset) for dataset in store.list_datasets()]


@market_data_router.post("/download")
def start_download(req: DownloadRequest):
    _cleanup_old_downloads()

    try:
        _resolve_symbol(req.contract_id)
        start = datetime.strptime(req.start_date, "%Y-%m-%d")
        end = datetime.strptime(req.end_date, "%Y-%m-%d").replace(hour=23, minute=59, second=59)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid date format: {exc}") from exc

    if start >= end:
        raise HTTPException(status_code=400, detail="start_date must be before end_date")

    with _downloads_lock:
        for download_id, info in ACTIVE_DOWNLOADS.items():
            if info.get("contract_id") == req.contract_id and info["status"] == "in_progress":
                raise HTTPException(
                    status_code=409,
                    detail=f"Download already in progress for {req.contract_id} (id: {download_id})",
                )

    download_id = str(uuid.uuid4())

    with _downloads_lock:
        ACTIVE_DOWNLOADS[download_id] = {
            "download_id": download_id,
            "contract_id": req.contract_id,
            "status": "in_progress",
            "progress": 0.0,
            "bars_downloaded": 0,
            "message": "Starting download...",
            "started_at": time.time(),
        }

    thread = threading.Thread(
        target=_run_download,
        args=(download_id, req.contract_id, start, end),
        daemon=True,
    )
    thread.start()

    logger.info("Started download %s for %s (%s to %s)", download_id, req.contract_id, req.start_date, req.end_date)
    return {"download_id": download_id, "message": "Download started"}


@market_data_router.get("/download/{download_id}/status", response_model=DownloadStatusResponse)
def get_download_status(download_id: str):
    with _downloads_lock:
        info = ACTIVE_DOWNLOADS.get(download_id)

    if info is None:
        raise HTTPException(status_code=404, detail=f"Download {download_id} not found")

    return DownloadStatusResponse(
        download_id=info["download_id"],
        status=info["status"],
        progress=info["progress"],
        bars_downloaded=info["bars_downloaded"],
        message=info["message"],
    )


@market_data_router.delete("/{dataset_id}")
def delete_dataset(dataset_id: str):
    deleted = store.delete_dataset(dataset_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Dataset {dataset_id} not found")
    return {"message": "Dataset deleted", "id": dataset_id}
