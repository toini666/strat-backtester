#!/usr/bin/env python3
"""
One-time script: Contract switch for MGC from M26 → Q26 (2026-05-27/28).

Context:
  - Existing data covers up to 2026-05-22 22:59 Brussels (CEST, UTC+2)
  - M26 (CON.F.US.MGC.M26) is active until 2026-05-27 22:59 Brussels (= 20:59 UTC)
  - The CME metals daily maintenance break is 17:00–18:00 ET = 23:00–00:00 Brussels CEST.
    So the trading session for 2026-05-28 opens at 00:00 Brussels on 2026-05-28
    (= 18:00 ET on 2026-05-27 = 22:00 UTC on 2026-05-27).
  - Q26 (CON.F.US.MGC.Q26 — August) becomes the front month from 2026-05-28 00:00 Brussels.
    NOTE: Q26 carries a contango premium over M26, so its first bar will open at a
    visibly different price than M26's last close. This is expected — do NOT treat the
    price jump as an error. Confirm the first Q26 bars against TradingView manually.

Steps:
  1. Fetch remaining M26 bars (2026-05-22 → 2026-05-27 20:59 UTC)
  2. Save with contract_id=M26 (appends to existing M26 data)
  3. Fetch Q26 bars (2026-05-27 22:00 UTC → now)
  4. Save with contract_id=Q26 (triggers contract roll in save_bars)
  5. Update SYMBOL_CONTRACTS in market_store.py

After running this script, update SYMBOL_CONTRACTS manually:
    "MGC": "CON.F.US.MGC.Q26"
"""
import sys
import os
import logging
from datetime import datetime

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
OLD_CONTRACT = "CON.F.US.MGC.M26"
NEW_CONTRACT = "CON.F.US.MGC.Q26"

# M26 fetch window: from May 22 (safe overlap) to May 27 20:59 UTC (= 22:59 Brussels CEST=UTC+2)
M26_START_UTC = datetime(2026, 5, 22, 20, 0, 0)   # 2026-05-22 20:00 UTC = 22:00 Brussels CEST
M26_END_UTC   = datetime(2026, 5, 27, 20, 59, 0)  # 2026-05-27 20:59 UTC = 22:59 Brussels CEST (last M26 bar)

# Q26 fetch window: from May 27 22:00 UTC (= 2026-05-28 00:00 Brussels, CME session open) to now
Q26_START_UTC = datetime(2026, 5, 27, 22, 0, 0)   # 2026-05-27 22:00 UTC = 2026-05-28 00:00 Brussels CEST
Q26_END_UTC   = datetime.utcnow()


def main():
    client = TopstepClient()
    store = MarketDataStore()

    # ---- Step 1: Fetch remaining M26 bars ----
    logger.info("=" * 60)
    logger.info(f"Step 1: Fetching {OLD_CONTRACT} bars")
    logger.info(f"  From: {M26_START_UTC} UTC")
    logger.info(f"  To:   {M26_END_UTC} UTC")
    logger.info("=" * 60)

    m26_data = client.fetch_historical_data(
        contract_id=OLD_CONTRACT,
        start=M26_START_UTC,
        end=M26_END_UTC,
        timeframe="1m",
        live=False,
    )

    if m26_data.empty:
        logger.warning("No M26 data returned — check if contract is still accessible in Topstep API")
    else:
        logger.info(f"Fetched {len(m26_data)} M26 bars: {m26_data.index.min()} → {m26_data.index.max()}")
        last_bar = m26_data.index.max()
        logger.info(f"Last M26 bar (Brussels): {last_bar}")
        # Sanity: no M26 bar should be at or after 21:00 UTC on 2026-05-27
        late = [ts for ts in m26_data.index if ts.tz_convert('UTC') >= __import__('pandas').Timestamp('2026-05-27 21:00', tz='UTC')]
        if late:
            logger.warning(f"  WARNING: {len(late)} M26 bars at/after 21:00 UTC on 27 May — should be none. e.g. {late[0]}")
        meta = store.save_bars(SYMBOL, OLD_CONTRACT, m26_data)
        logger.info(f"Saved M26 data. Dataset now: {meta['start_date']} → {meta['end_date']} ({meta['bar_count_1m']} bars)")

    # ---- Step 2: Fetch Q26 bars ----
    logger.info("=" * 60)
    logger.info(f"Step 2: Fetching {NEW_CONTRACT} bars")
    logger.info(f"  From: {Q26_START_UTC} UTC")
    logger.info(f"  To:   {Q26_END_UTC.strftime('%Y-%m-%d %H:%M:%S')} UTC (now)")
    logger.info("=" * 60)

    q26_data = client.fetch_historical_data(
        contract_id=NEW_CONTRACT,
        start=Q26_START_UTC,
        end=Q26_END_UTC,
        timeframe="1m",
        live=False,
    )

    if q26_data.empty:
        logger.error(f"No Q26 data returned — contract ID '{NEW_CONTRACT}' may be wrong (format/month). STOPPING; not saving.")
        return 1

    logger.info(f"Fetched {len(q26_data)} Q26 bars: {q26_data.index.min()} → {q26_data.index.max()}")

    # Log first 10 Q26 bars for manual TradingView verification (do NOT hard-fail on price:
    # Q26 carries a contango premium over M26 so a price jump across the roll is expected).
    logger.info("First 10 Q26 bars (Brussels time) — verify against TradingView:")
    for ts, row in q26_data.head(10).iterrows():
        logger.info(f"  {ts}  O={row['Open']}  H={row['High']}  L={row['Low']}  C={row['Close']}")

    first_bar = q26_data.index.min()
    expected_first = __import__('pandas').Timestamp('2026-05-28 00:00', tz='Europe/Brussels')
    if first_bar == expected_first:
        logger.info(f"✓ First Q26 bar is exactly {first_bar} (= 00:00 Brussels 28 May) as expected")
    else:
        logger.warning(f"✗ First Q26 bar is {first_bar}, expected {expected_first}")

    meta = store.save_bars(SYMBOL, NEW_CONTRACT, q26_data)
    logger.info(f"Saved Q26 data. Dataset now: {meta['start_date']} → {meta['end_date']} ({meta['bar_count_1m']} bars)")
    logger.info(f"Contract segments: {meta['contract_segments']}")

    # ---- Done ----
    logger.info("=" * 60)
    logger.info("Contract switch complete!")
    logger.info("IMPORTANT: Update SYMBOL_CONTRACTS in src/data/market_store.py:")
    logger.info(f'    "MGC": "{NEW_CONTRACT}",')
    logger.info("=" * 60)

    return 0


if __name__ == "__main__":
    sys.exit(main())
