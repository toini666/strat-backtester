#!/usr/bin/env python3
"""
Download and update local market data for all tracked assets.

Usage:
    python scripts/update_market_data.py                  # Update all assets
    python scripts/update_market_data.py MNQ MES          # Update specific assets
    python scripts/update_market_data.py --full-reload    # Re-download everything from scratch
    python scripts/update_market_data.py --rebuild-only   # Rebuild derived timeframe CSVs from local 1m data
"""
import argparse
import logging
import sys
import os
import time
from datetime import datetime, timedelta

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from dotenv import load_dotenv
load_dotenv()

from src.data.topstep import TopstepClient
from src.data.market_store import MarketDataStore, SYMBOL_CONTRACTS

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger(__name__)


def download_asset(client: TopstepClient, store: MarketDataStore, symbol: str, full_reload: bool = False):
    """Download 1m bars for a single asset and generate all timeframes."""
    contract_id = SYMBOL_CONTRACTS.get(symbol)
    if not contract_id:
        logger.error(f"Unknown symbol: {symbol}. Known: {list(SYMBOL_CONTRACTS.keys())}")
        return False

    logger.info(f"{'=' * 60}")
    logger.info(f"Processing {symbol} ({contract_id})")
    logger.info(f"{'=' * 60}")

    # Determine date range
    existing = store.get_dataset_by_symbol(symbol)

    if existing and not full_reload:
        # Incremental update: fetch from last known bar to now
        last_date = existing["end_date"]
        # Parse and go back 1 day to catch any gaps
        start = datetime.fromisoformat(str(last_date).replace("+00:00", "").replace("+01:00", "").replace("+02:00", "")) - timedelta(days=1)
        logger.info(f"Incremental update from {start.date()} (last data: {last_date})")
    else:
        # Full download: go back as far as possible
        # Topstep keeps ~2 months of 1m data
        start = datetime.utcnow() - timedelta(days=75)
        logger.info(f"Full download from {start.date()}")

    end = datetime.utcnow()

    # Download 1m bars
    try:
        logger.info(f"Fetching 1m bars from Topstep API... (this may take a few minutes)")
        data = client.fetch_historical_data(
            contract_id=contract_id,
            start=start,
            end=end,
            timeframe="1m",
            live=False,
        )
    except Exception as e:
        logger.error(f"Failed to fetch data for {symbol}: {e}")
        return False

    if data.empty:
        logger.warning(f"No 1m data returned for {symbol}")
        return False

    logger.info(f"Downloaded {len(data)} 1m bars ({data.index.min()} to {data.index.max()})")

    # Save to store (handles merge, timezone conversion, and recomposition)
    metadata = store.save_bars(symbol, contract_id, data)

    logger.info(f"Done: {symbol} - {metadata['bar_count_1m']} bars, {metadata['total_size_mb']} MB")
    logger.info(f"  Range: {metadata['start_date']} to {metadata['end_date']}")
    logger.info(f"  Timeframes: {', '.join(metadata['timeframes'])}")

    return True


def main():
    parser = argparse.ArgumentParser(description="Download/update local market data")
    parser.add_argument("symbols", nargs="*", help="Symbols to update (default: all)")
    parser.add_argument("--full-reload", action="store_true", help="Re-download from scratch")
    parser.add_argument("--rebuild-only", action="store_true", help="Only rebuild derived timeframe CSVs from local 1m data")
    args = parser.parse_args()

    symbols = args.symbols if args.symbols else list(SYMBOL_CONTRACTS.keys())

    logger.info(f"Updating market data for: {', '.join(symbols)}")

    store = MarketDataStore()
    if args.rebuild_only:
        rebuilt = store.rebuild_recomposed_data(symbols)
        logger.info("")
        logger.info("=" * 60)
        logger.info("REBUILD SUMMARY")
        logger.info("=" * 60)
        for ds in rebuilt:
            logger.info(
                f"  {ds['symbol']:>4s}: rebuilt | {ds['bar_count_1m']:>6} bars | "
                f"{ds['start_date'][:10]} to {ds['end_date'][:10]} | {ds['total_size_mb']} MB"
            )
        return 0

    client = TopstepClient()

    results = {}
    for i, symbol in enumerate(symbols):
        success = download_asset(client, store, symbol, args.full_reload)
        results[symbol] = success

        # Small delay between assets to be nice to the API
        if i < len(symbols) - 1:
            logger.info("Waiting 2s before next asset...")
            time.sleep(2)

    # Summary
    logger.info("")
    logger.info("=" * 60)
    logger.info("SUMMARY")
    logger.info("=" * 60)
    for symbol, success in results.items():
        status = "OK" if success else "FAILED"
        ds = store.get_dataset_by_symbol(symbol)
        if ds:
            logger.info(f"  {symbol:>4s}: {status} | {ds['bar_count_1m']:>6} bars | {ds['start_date'][:10]} to {ds['end_date'][:10]} | {ds['total_size_mb']} MB")
        else:
            logger.info(f"  {symbol:>4s}: {status} | no data")

    failed = [s for s, ok in results.items() if not ok]
    if failed:
        logger.warning(f"Failed: {', '.join(failed)}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
