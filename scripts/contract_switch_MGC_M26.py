#!/usr/bin/env python3
"""
One-time script: Contract switch for MGC from J26 → M26 (2026-03-30).

Context:
  - Existing data covers up to 2026-03-27 21:59 Brussels (CET, UTC+1)
  - J26 (CON.F.US.MGC.J26) was active until 2026-03-27 21:59 Brussels
  - Brussels switched to CEST (UTC+2) on Sunday 2026-03-29
  - M26 (CON.F.US.MGC.M26) opened Sunday 2026-03-29 23:00 Brussels CEST (= 21:00 UTC)
    [CME opens 17:00 EDT = 21:00 UTC; Brussels CEST=UTC+2 → 23:00 Brussels]
  - Verification: first bar at 0h00 Brussels on 30/3 (= 22:00 UTC 29/3) opens at 4517.8

Steps:
  1. Fetch remaining J26 bars (2026-03-26 → 2026-03-27 20:59 UTC)
  2. Save with contract_id=J26 (appends to existing J26 data)
  3. Fetch M26 bars (2026-03-29 21:00 UTC → now)
  4. Save with contract_id=M26 (triggers contract roll in save_bars)
  5. Update SYMBOL_CONTRACTS in market_store.py

After running this script, update SYMBOL_CONTRACTS manually:
    "MGC": "CON.F.US.MGC.M26"
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

SYMBOL = "MGC"
OLD_CONTRACT = "CON.F.US.MGC.J26"
NEW_CONTRACT = "CON.F.US.MGC.M26"

# J26 fetch window: from March 26 (safe overlap) to March 27 20:59 UTC (= 21:59 Brussels CET=UTC+1)
J26_START_UTC = datetime(2026, 3, 26, 21, 0, 0)   # 2026-03-26 21:00 UTC = 2026-03-26 22:00 Brussels CET
J26_END_UTC   = datetime(2026, 3, 27, 20, 59, 0)  # 2026-03-27 20:59 UTC = 2026-03-27 21:59 Brussels CET

# M26 fetch window: from March 29 21:00 UTC (= 23:00 Brussels CEST, CME Sunday open) to now
M26_START_UTC = datetime(2026, 3, 29, 21, 0, 0)   # 2026-03-29 21:00 UTC = 2026-03-29 23:00 Brussels CEST
M26_END_UTC   = datetime.utcnow()


def main():
    client = TopstepClient()
    store = MarketDataStore()

    # ---- Step 1: Fetch remaining J26 bars ----
    logger.info("=" * 60)
    logger.info(f"Step 1: Fetching {OLD_CONTRACT} bars")
    logger.info(f"  From: {J26_START_UTC} UTC")
    logger.info(f"  To:   {J26_END_UTC} UTC")
    logger.info("=" * 60)

    j26_data = client.fetch_historical_data(
        contract_id=OLD_CONTRACT,
        start=J26_START_UTC,
        end=J26_END_UTC,
        timeframe="1m",
        live=False,
    )

    if j26_data.empty:
        logger.warning(f"No J26 data returned — check if contract is still accessible in Topstep API")
    else:
        logger.info(f"Fetched {len(j26_data)} J26 bars: {j26_data.index.min()} → {j26_data.index.max()}")
        # Verify last bar is around 2026-03-27 21:59 Brussels
        last_bar = j26_data.index.max()
        logger.info(f"Last J26 bar (Brussels): {last_bar}")
        meta = store.save_bars(SYMBOL, OLD_CONTRACT, j26_data)
        logger.info(f"Saved J26 data. Dataset now: {meta['start_date']} → {meta['end_date']} ({meta['bar_count_1m']} bars)")

    # ---- Step 2: Fetch M26 bars ----
    logger.info("=" * 60)
    logger.info(f"Step 2: Fetching {NEW_CONTRACT} bars")
    logger.info(f"  From: {M26_START_UTC} UTC")
    logger.info(f"  To:   {M26_END_UTC.strftime('%Y-%m-%d %H:%M:%S')} UTC (now)")
    logger.info("=" * 60)

    m26_data = client.fetch_historical_data(
        contract_id=NEW_CONTRACT,
        start=M26_START_UTC,
        end=M26_END_UTC,
        timeframe="1m",
        live=False,
    )

    if m26_data.empty:
        logger.error(f"No M26 data returned — cannot complete contract switch!")
        return 1

    logger.info(f"Fetched {len(m26_data)} M26 bars: {m26_data.index.min()} → {m26_data.index.max()}")

    # Verify: first bar at 00:00 Brussels on 2026-03-30 should have Open=4517.8
    # 00:00 Brussels CEST = 22:00 UTC on 2026-03-29
    target_ts = "2026-03-30 00:00"  # Brussels time
    first_bars = m26_data.head(10)
    logger.info(f"First 10 M26 bars (Brussels time):")
    for ts, row in first_bars.iterrows():
        logger.info(f"  {ts}  O={row['Open']}  H={row['High']}  L={row['Low']}  C={row['Close']}")

    # Check if bar at 00:00 Brussels on 30/3 matches expected Open=4517.8
    matching = [ts for ts in m26_data.index if str(ts).startswith("2026-03-30 00:00")]
    if matching:
        bar = m26_data.loc[matching[0]]
        expected_open = 4517.8
        if abs(bar['Open'] - expected_open) < 0.1:
            logger.info(f"✓ Verification PASSED: bar at {matching[0]} Open={bar['Open']} matches expected {expected_open}")
        else:
            logger.warning(f"✗ Verification FAILED: bar at {matching[0]} Open={bar['Open']} != expected {expected_open}")
            logger.warning("  Check if this is the correct contract or if the switch date is wrong!")
    else:
        logger.warning(f"  Could not find bar at 2026-03-30 00:00 Brussels for verification")

    meta = store.save_bars(SYMBOL, NEW_CONTRACT, m26_data)
    logger.info(f"Saved M26 data. Dataset now: {meta['start_date']} → {meta['end_date']} ({meta['bar_count_1m']} bars)")
    logger.info(f"Contract segments: {meta['contract_segments']}")

    # ---- Done ----
    logger.info("=" * 60)
    logger.info("Contract switch complete!")
    logger.info(f"IMPORTANT: Update SYMBOL_CONTRACTS in src/data/market_store.py:")
    logger.info(f'    "MGC": "{NEW_CONTRACT}",')
    logger.info("=" * 60)

    return 0


if __name__ == "__main__":
    sys.exit(main())
