#!/usr/bin/env python3
"""
One-time script: Contract switch for MCL from M26 → N26 (2026-05-15).

Context:
  - Existing local data was downloaded for CON.F.US.MCLE.M26 up to 2026-05-15 22:59
    Brussels, but front-month rolled to N26 at the CME daily reopen on
    2026-05-14 22:00 UTC = 2026-05-15 00:00 Brussels (CEST, UTC+2).
  - Cross-check vs TradingView (Brussels time, CEST):
        14/5 22:59  TV: O=102.03 C=102.03  M26: 102.03 / 102.03  N26: ~97.80
        15/5 00:00  TV: O=97.80  C=97.86   M26: 102.02 / 101.98  N26: 97.80 / 97.86
    → N26 is the right front-month from 15/5 00:00 Brussels onward.

Steps:
  1. Truncate MCL_1m.csv at 2026-05-14 22:59 Brussels (last valid M26 close).
  2. Rewrite metadata so end_date = 2026-05-14 22:59 Brussels (so save_bars'
     merge will accept the N26 bars starting at 00:00 Friday).
  3. Fetch N26 (CON.F.US.MCLE.N26) bars from 2026-05-14 22:00 UTC to now.
  4. save_bars(MCL, N26, ...) — detects contract change, appends, updates
     contract_segments, regenerates higher timeframes.
  5. Manually update SYMBOL_CONTRACTS["MCL"] in src/data/market_store.py.
"""
import sys
import os
import json
import logging
from datetime import datetime
from pathlib import Path

import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from dotenv import load_dotenv
load_dotenv()

from src.data.topstep import TopstepClient
from src.data.market_store import MarketDataStore, BRUSSELS_TZ

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger(__name__)

SYMBOL = "MCL"
OLD_CONTRACT = "CON.F.US.MCLE.M26"
NEW_CONTRACT = "CON.F.US.MCLE.N26"

# Truncate boundary: keep bars with timestamp ≤ this point (Thu close, Brussels CEST).
TRUNCATE_AT_BRUSSELS = pd.Timestamp("2026-05-14 22:59:00", tz=BRUSSELS_TZ)

# N26 fetch window: from 22:00 UTC on 2026-05-14 (= 00:00 Brussels CEST on 2026-05-15) to now.
N26_START_UTC = datetime(2026, 5, 14, 22, 0, 0)
N26_END_UTC   = datetime.utcnow()


def truncate_existing_csv(store: MarketDataStore) -> None:
    """Trim MCL_1m.csv so it ends at TRUNCATE_AT_BRUSSELS, and update index accordingly."""
    csv_path = store.data_dir / SYMBOL / f"{SYMBOL}_1m.csv"
    if not csv_path.exists():
        logger.warning(f"{csv_path} does not exist — nothing to truncate")
        return

    df = pd.read_csv(csv_path, index_col="Date")
    df.index = pd.to_datetime(df.index, utc=True).tz_convert(BRUSSELS_TZ)
    before = len(df)
    df = df[df.index <= TRUNCATE_AT_BRUSSELS]
    after = len(df)
    logger.info(f"Truncated {SYMBOL}_1m.csv: {before} → {after} bars  (cut {before - after} M26 bars after {TRUNCATE_AT_BRUSSELS})")
    df.to_csv(csv_path, index_label="Date")

    # Update index entry: rewrite end_date so save_bars merge logic accepts new bars.
    index = store._load_index()
    for entry in index:
        if entry.get("symbol") == SYMBOL:
            entry["contract_id"] = OLD_CONTRACT  # still M26 at this point
            entry["end_date"] = str(df.index.max())
            entry["bar_count_1m"] = len(df)
            # Trim the open segment if it ran past the truncate date
            segs = entry.get("contract_segments", [])
            if segs and segs[-1]["contract"] == OLD_CONTRACT:
                segs[-1]["to"] = str(df.index.max().date())
            break
    store._save_index(index)
    logger.info(f"Index updated: end_date = {df.index.max()}")


def main():
    client = TopstepClient()
    store = MarketDataStore()

    # ---- Step 1: Truncate existing CSV at Thu close ----
    logger.info("=" * 60)
    logger.info(f"Step 1: Truncate {SYMBOL}_1m.csv at {TRUNCATE_AT_BRUSSELS}")
    logger.info("=" * 60)
    truncate_existing_csv(store)

    # ---- Step 2: Fetch N26 bars from Fri 00:00 Brussels onward ----
    logger.info("=" * 60)
    logger.info(f"Step 2: Fetching {NEW_CONTRACT} bars")
    logger.info(f"  From: {N26_START_UTC} UTC (= 2026-05-15 00:00 Brussels CEST)")
    logger.info(f"  To:   {N26_END_UTC.strftime('%Y-%m-%d %H:%M:%S')} UTC (now)")
    logger.info("=" * 60)

    n26_data = client.fetch_historical_data(
        contract_id=NEW_CONTRACT,
        start=N26_START_UTC,
        end=N26_END_UTC,
        timeframe="1m",
        live=False,
    )

    if n26_data.empty:
        logger.error("No N26 data returned — cannot complete contract switch")
        return 1

    logger.info(f"Fetched {len(n26_data)} N26 bars: {n26_data.index.min()} → {n26_data.index.max()}")

    # Verification: first Friday 00:00 Brussels bar should be ~97.80 open (matches TV)
    n26_brussels = n26_data.copy()
    n26_brussels.index = n26_brussels.index.tz_convert(BRUSSELS_TZ) if n26_brussels.index.tz else n26_brussels.index.tz_localize("UTC").tz_convert(BRUSSELS_TZ)
    target = "2026-05-15 00:00"
    matching = [ts for ts in n26_brussels.index if str(ts).startswith(target)]
    if matching:
        bar = n26_brussels.loc[matching[0]]
        expected_open = 97.80
        if abs(bar["Open"] - expected_open) < 0.2:
            logger.info(f"✓ Verification PASSED: bar at {matching[0]} Open={bar['Open']} matches TV expected {expected_open}")
        else:
            logger.warning(f"✗ Verification: bar at {matching[0]} Open={bar['Open']} differs from TV expected {expected_open}")
    else:
        logger.warning(f"  Could not find bar at {target} Brussels for verification")

    # ---- Step 3: Save (creates new segment) ----
    logger.info("=" * 60)
    logger.info("Step 3: save_bars — append N26, update segments, regen higher TFs")
    logger.info("=" * 60)
    meta = store.save_bars(SYMBOL, NEW_CONTRACT, n26_data)
    logger.info(f"Dataset now: {meta['start_date']} → {meta['end_date']}  ({meta['bar_count_1m']} bars)")
    logger.info(f"Contract segments: {json.dumps(meta['contract_segments'], indent=2)}")

    logger.info("=" * 60)
    logger.info("Contract switch complete.")
    logger.info('IMPORTANT: Update SYMBOL_CONTRACTS in src/data/market_store.py:')
    logger.info(f'    "MCL": "{NEW_CONTRACT}",')
    logger.info("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
