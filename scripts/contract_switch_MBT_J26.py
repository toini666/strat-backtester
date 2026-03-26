#!/usr/bin/env python3
"""
One-time script: Contract switch for MBT from H26 → J26 (2026-03-26).

Context:
  - Existing data covers up to 2026-03-20 21:59 Brussels (CET, UTC+1)
  - H26 (CON.F.US.MBT.H26) was active until 2026-03-26 21:59 Brussels
  - J26 (CON.F.US.MBT.J26) opened 2026-03-26 23:00 Brussels (= 22:00 UTC)
    [Note: March 26 Brussels=CET=UTC+1, US=EDT=UTC-4, CME opens 17:00 EDT = 22:00 UTC]

Steps:
  1. Fetch remaining H26 bars (2026-03-20 → 2026-03-26 21:59 Brussels)
  2. Save with contract_id=H26 (appends to existing H26 data)
  3. Fetch J26 bars (2026-03-26 23:00 Brussels → now)
  4. Save with contract_id=J26 (triggers contract roll in save_bars)
  5. Update SYMBOL_CONTRACTS in market_store.py

After running this script, update SYMBOL_CONTRACTS manually:
    "MBT": "CON.F.US.MBT.J26"
"""
import sys
import os
import logging
from datetime import datetime, timezone

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from dotenv import load_dotenv
load_dotenv()

from src.data.topstep import TopstepClient
from src.data.market_store import MarketDataStore

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger(__name__)

SYMBOL = "MBT"
OLD_CONTRACT = "CON.F.US.MBT.H26"
NEW_CONTRACT = "CON.F.US.MBT.J26"

# H26 fetch window: from March 19 (safe overlap) to March 26 21:59 Brussels (CET=UTC+1 → 20:59 UTC)
H26_START_UTC = datetime(2026, 3, 19, 22, 0, 0)   # 2026-03-19 22:00 UTC = 2026-03-19 23:00 Brussels
H26_END_UTC   = datetime(2026, 3, 26, 20, 59, 0)  # 2026-03-26 20:59 UTC = 2026-03-26 21:59 Brussels

# J26 fetch window: from March 26 22:00 UTC (= 23:00 Brussels, CME open) to now
J26_START_UTC = datetime(2026, 3, 26, 22, 0, 0)   # 2026-03-26 22:00 UTC = 2026-03-26 23:00 Brussels
J26_END_UTC   = datetime.utcnow()


def main():
    client = TopstepClient()
    store = MarketDataStore()

    # ---- Step 1: Fetch remaining H26 bars ----
    logger.info("=" * 60)
    logger.info(f"Step 1: Fetching {OLD_CONTRACT} bars")
    logger.info(f"  From: {H26_START_UTC} UTC")
    logger.info(f"  To:   {H26_END_UTC} UTC")
    logger.info("=" * 60)

    h26_data = client.fetch_historical_data(
        contract_id=OLD_CONTRACT,
        start=H26_START_UTC,
        end=H26_END_UTC,
        timeframe="1m",
        live=False,
    )

    if h26_data.empty:
        logger.warning(f"No H26 data returned — check if contract is still accessible in Topstep API")
    else:
        logger.info(f"Fetched {len(h26_data)} H26 bars: {h26_data.index.min()} → {h26_data.index.max()}")
        meta = store.save_bars(SYMBOL, OLD_CONTRACT, h26_data)
        logger.info(f"Saved H26 data. Dataset now: {meta['start_date']} → {meta['end_date']} ({meta['bar_count_1m']} bars)")

    # ---- Step 2: Fetch J26 bars ----
    logger.info("=" * 60)
    logger.info(f"Step 2: Fetching {NEW_CONTRACT} bars")
    logger.info(f"  From: {J26_START_UTC} UTC")
    logger.info(f"  To:   {J26_END_UTC.strftime('%Y-%m-%d %H:%M:%S')} UTC (now)")
    logger.info("=" * 60)

    j26_data = client.fetch_historical_data(
        contract_id=NEW_CONTRACT,
        start=J26_START_UTC,
        end=J26_END_UTC,
        timeframe="1m",
        live=False,
    )

    if j26_data.empty:
        logger.error(f"No J26 data returned — cannot complete contract switch!")
        return 1

    logger.info(f"Fetched {len(j26_data)} J26 bars: {j26_data.index.min()} → {j26_data.index.max()}")
    meta = store.save_bars(SYMBOL, NEW_CONTRACT, j26_data)
    logger.info(f"Saved J26 data. Dataset now: {meta['start_date']} → {meta['end_date']} ({meta['bar_count_1m']} bars)")
    logger.info(f"Contract segments: {meta['contract_segments']}")

    # ---- Done ----
    logger.info("=" * 60)
    logger.info("Contract switch complete!")
    logger.info(f"IMPORTANT: Update SYMBOL_CONTRACTS in src/data/market_store.py:")
    logger.info(f'    "MBT": "{NEW_CONTRACT}",')
    logger.info("=" * 60)

    return 0


if __name__ == "__main__":
    sys.exit(main())
