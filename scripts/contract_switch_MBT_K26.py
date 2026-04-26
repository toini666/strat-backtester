#!/usr/bin/env python3
"""
One-time script: Contract switch for MBT from J26 → K26 (2026-04-22).

Context:
  - Existing data covers J26 (CON.F.US.MBT.J26) from 2026-01-15 through 2026-04-24 16:58 Brussels CEST
  - BUT the front-month switched at session open on 2026-04-22 00:00 Brussels CEST
  - TV verification: last J26 bar 2026-04-21 22:59 = Open 75810 / Close 75735 ✓ (matches our data)
  - TV first K26 bar 2026-04-22 00:00 = Open 76000 / Close 75920
  - Our data for 2026-04-22 00:00 shows Open 75405 → still J26 data (wrong contract)
  - J26 (April) expires 2026-04-24 (last Friday of April)
  - K26 (May) = CON.F.US.MBT.K26

Steps:
  1. Trim existing MBT_1m.csv to end at 2026-04-21 22:59 Brussels (last valid J26 bar)
  2. Update index.json end_date for MBT to match
  3. Fetch K26 bars from 2026-04-21 22:00 UTC (= 2026-04-22 00:00 Brussels CEST) to now
  4. Save with contract_id=K26 (save_bars detects contract change, appends only after existing_end)
  5. Update SYMBOL_CONTRACTS in market_store.py to K26
"""
import sys
import os
import json
import logging
from datetime import datetime, timezone

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from dotenv import load_dotenv
load_dotenv()

import pandas as pd
from src.data.topstep import TopstepClient
from src.data.market_store import MarketDataStore, DATA_DIR

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger(__name__)

SYMBOL       = "MBT"
OLD_CONTRACT = "CON.F.US.MBT.J26"
NEW_CONTRACT = "CON.F.US.MBT.K26"

# Last valid J26 bar: 2026-04-21 22:59 Brussels CEST (UTC+2) = 2026-04-21 20:59 UTC
J26_LAST_BAR_BRUSSELS = pd.Timestamp("2026-04-21 22:59:00", tz="Europe/Brussels")

# K26 fetch window: CME session open on 2026-04-22 = 22:00 UTC on 2026-04-21 (Brussels CEST=UTC+2 → 00:00)
K26_START_UTC = datetime(2026, 4, 21, 22, 0, 0, tzinfo=timezone.utc)
K26_END_UTC   = datetime.now(tz=timezone.utc)


def main():
    store = MarketDataStore()
    client = TopstepClient()

    symbol_dir = DATA_DIR / SYMBOL
    csv_1m_path = symbol_dir / f"{SYMBOL}_1m.csv"
    index_path  = DATA_DIR / "index.json"

    # ---- Step 1: Trim existing CSV to last valid J26 bar ----
    logger.info("=" * 60)
    logger.info(f"Step 1: Trim {SYMBOL}_1m.csv to {J26_LAST_BAR_BRUSSELS}")
    logger.info("=" * 60)

    existing = pd.read_csv(csv_1m_path, index_col="Date")
    existing.index = pd.to_datetime(existing.index, utc=True).tz_convert("Europe/Brussels")

    before = len(existing)
    trimmed = existing[existing.index <= J26_LAST_BAR_BRUSSELS]
    after   = len(trimmed)

    logger.info(f"Rows before trim: {before}")
    logger.info(f"Rows after trim:  {after} (removed {before - after} wrong-contract bars)")
    logger.info(f"Last bar after trim: {trimmed.index.max()}")

    # Verify last bar matches TV data
    last_bar = trimmed.iloc[-1]
    expected_open, expected_close = 75810.0, 75735.0
    if abs(last_bar['Open'] - expected_open) < 1 and abs(last_bar['Close'] - expected_close) < 1:
        logger.info(f"✓ Verification PASSED: last bar Open={last_bar['Open']} Close={last_bar['Close']} matches TV")
    else:
        logger.warning(f"✗ Verification WARNING: last bar Open={last_bar['Open']} Close={last_bar['Close']} "
                       f"expected Open={expected_open} Close={expected_close}")

    trimmed.to_csv(csv_1m_path, index_label="Date")
    logger.info(f"Saved trimmed CSV to {csv_1m_path}")

    # ---- Step 2: Update index.json end_date ----
    logger.info("=" * 60)
    logger.info("Step 2: Update index.json end_date for MBT")
    logger.info("=" * 60)

    with open(index_path, "r") as f:
        index = json.load(f)

    for entry in index:
        if entry.get("symbol") == SYMBOL:
            old_end = entry["end_date"]
            entry["end_date"]       = str(trimmed.index.max())
            entry["bar_count_1m"]   = len(trimmed)
            logger.info(f"Updated end_date: {old_end} → {entry['end_date']}")
            break

    with open(index_path, "w") as f:
        json.dump(index, f, indent=2)
    logger.info("index.json updated")

    # ---- Step 3: Fetch K26 bars ----
    logger.info("=" * 60)
    logger.info(f"Step 3: Fetch {NEW_CONTRACT} bars")
    logger.info(f"  From: {K26_START_UTC}  (= 2026-04-22 00:00 Brussels CEST)")
    logger.info(f"  To:   {K26_END_UTC.strftime('%Y-%m-%d %H:%M:%S UTC')} (now)")
    logger.info("=" * 60)

    k26_data = client.fetch_historical_data(
        contract_id=NEW_CONTRACT,
        start=K26_START_UTC,
        end=K26_END_UTC,
        timeframe="1m",
        live=False,
    )

    if k26_data.empty:
        logger.error(f"No K26 data returned — check contract ID or Topstep availability")
        return 1

    logger.info(f"Fetched {len(k26_data)} K26 bars: {k26_data.index.min()} → {k26_data.index.max()}")

    # Verify first bar matches TV: 2026-04-22 00:00 Brussels → Open 76000, Close 75920
    k26_brussels = k26_data.copy()
    k26_brussels.index = pd.to_datetime(k26_brussels.index, utc=True).tz_convert("Europe/Brussels")
    target = "2026-04-22 00:00"
    matching = [ts for ts in k26_brussels.index if str(ts).startswith(target)]
    if matching:
        bar = k26_brussels.loc[matching[0]]
        exp_open, exp_close = 76000.0, 75920.0
        if abs(bar['Open'] - exp_open) < 5 and abs(bar['Close'] - exp_close) < 5:
            logger.info(f"✓ Verification PASSED: {matching[0]} Open={bar['Open']} Close={bar['Close']} matches TV")
        else:
            logger.warning(f"✗ Verification FAILED: {matching[0]} Open={bar['Open']} Close={bar['Close']} "
                           f"expected Open={exp_open} Close={exp_close}")
            logger.warning("  Prices may differ slightly (Topstep vs TV) but order of magnitude should match")
    else:
        logger.warning(f"  Could not find bar at {target} Brussels for TV verification")

    # ---- Step 4: Save K26 via save_bars ----
    logger.info("=" * 60)
    logger.info("Step 4: Save K26 data (contract switch)")
    logger.info("=" * 60)

    meta = store.save_bars(SYMBOL, NEW_CONTRACT, k26_data)
    logger.info(f"Saved. Dataset now: {meta['start_date']} → {meta['end_date']} ({meta['bar_count_1m']} bars)")
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
