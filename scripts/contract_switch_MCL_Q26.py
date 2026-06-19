#!/usr/bin/env python3
"""
One-time script: Contract switch for MCL from N26 → Q26 (2026-06-17).

Context:
  - Local MCL data was last updated to 2026-05-29 ~07:40 Brussels, on the N26
    (July) contract.
  - Front month rolls to Q26 (August) from the CME energy reopen on
    2026-06-16 18:00 ET = 2026-06-16 22:00 UTC = 2026-06-17 00:00 Brussels (CEST).
    The user designates Wednesday 2026-06-17 00:00 Brussels as the switch point.
  - Crude (MCL) has the same 17:00–18:00 ET daily maintenance as metals: the break
    is 23:00–00:00 Brussels, so the last N26 bar is 22:59 Brussels and the first
    Q26 bar is 00:00 Brussels of the next day.
  - CRITICAL: N26 (July crude) is still a LIVE contract after this roll (it does not
    expire until ~2026-06-22). It keeps trading through the 2026-06-17 00:00 Brussels
    reopen. So the N26 fetch MUST be capped strictly BEFORE the boundary, otherwise a
    stray N26 bar lands in the Q26 window, save_bars sets end_date there, and the real
    first Q26 bar gets dropped (df[df.index > existing_end]). Cap at 22:59 Brussels.
  - Q26 carries a roll premium/discount vs N26 — the first Q26 bar opens at a
    visibly different price. Expected; log for manual TradingView eyeball, do NOT
    hard-fail on it.

Steps:
  1. Fetch remaining N26 bars (overlap ~2026-05-28 → 2026-06-16 20:59 UTC = 22:59
     Brussels, last bar before the energy break), save as N26 (pure append).
  2. Fetch Q26 bars (2026-06-16 22:00 UTC = 2026-06-17 00:00 Brussels → now),
     save as Q26 (triggers the roll: new contract segment).
  3. Verify last N26 bar = 2026-06-16 22:59 Brussels, first Q26 bar = 2026-06-17 00:00.

After running, update SYMBOL_CONTRACTS in src/data/market_store.py:
    "MCL": "CON.F.US.MCLE.Q26"
"""
import sys
import os
import json
import logging
from datetime import datetime

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
OLD_CONTRACT = "CON.F.US.MCLE.N26"
NEW_CONTRACT = "CON.F.US.MCLE.Q26"

# N26 fill window: overlap into existing data → capped at 20:59 UTC (= 22:59 Brussels),
# the last N26 bar before the 23:00–00:00 Brussels energy maintenance break.
N26_START_UTC = datetime(2026, 5, 28, 0, 0, 0)
N26_END_UTC   = datetime(2026, 6, 16, 20, 59, 0)   # = 2026-06-16 22:59 Brussels (CEST), last N26 bar

# Q26 fetch window: energy reopen → now.
Q26_START_UTC = datetime(2026, 6, 16, 22, 0, 0)    # = 2026-06-17 00:00 Brussels (CEST)
Q26_END_UTC   = datetime.utcnow()

EXPECTED_LAST_N26  = pd.Timestamp("2026-06-16 22:59", tz=BRUSSELS_TZ)
EXPECTED_FIRST_Q26 = pd.Timestamp("2026-06-17 00:00", tz=BRUSSELS_TZ)


def main():
    client = TopstepClient()
    store = MarketDataStore()

    logger.info("=" * 64)
    logger.info(f"Step 1: fill {OLD_CONTRACT} ({N26_START_UTC} → {N26_END_UTC} UTC)")
    logger.info("=" * 64)

    n26 = client.fetch_historical_data(
        contract_id=OLD_CONTRACT, start=N26_START_UTC, end=N26_END_UTC,
        timeframe="1m", live=False,
    )
    if n26.empty:
        logger.error("No N26 data returned — cannot fill May29→Jun16 gap. "
                     "ABORTING to avoid a silent 3-week hole before Q26.")
        return 1

    last_n26 = n26.index.max()
    logger.info(f"Fetched {len(n26)} N26 bars: {n26.index.min()} → {last_n26}")
    if last_n26 == EXPECTED_LAST_N26:
        logger.info(f"✓ Last N26 bar is exactly {last_n26} (22:59 Brussels 16/06).")
    else:
        logger.warning(f"✗ Last N26 bar is {last_n26}, expected {EXPECTED_LAST_N26}.")
    meta = store.save_bars(SYMBOL, OLD_CONTRACT, n26)
    logger.info(f"N26 saved. Dataset now: {meta['start_date']} → {meta['end_date']} ({meta['bar_count_1m']} bars)")

    logger.info("=" * 64)
    logger.info(f"Step 2: fetch {NEW_CONTRACT} ({Q26_START_UTC} UTC = 2026-06-17 00:00 Brussels → now)")
    logger.info("=" * 64)

    q26 = client.fetch_historical_data(
        contract_id=NEW_CONTRACT, start=Q26_START_UTC, end=Q26_END_UTC,
        timeframe="1m", live=False,
    )
    if q26.empty:
        logger.error(f"No Q26 data returned — contract ID '{NEW_CONTRACT}' may be wrong. NOT saving.")
        return 1

    first_q26 = q26.index.min()
    logger.info(f"Fetched {len(q26)} Q26 bars: {first_q26} → {q26.index.max()}")
    logger.info("First 5 Q26 bars (Brussels) — eyeball vs TradingView (roll premium expected):")
    for ts, row in q26.head(5).iterrows():
        logger.info(f"    {ts}  O={row['Open']}  H={row['High']}  L={row['Low']}  C={row['Close']}")

    if first_q26 == EXPECTED_FIRST_Q26:
        logger.info(f"✓ First Q26 bar is exactly {first_q26} (00:00 Brussels 17/06).")
    else:
        logger.warning(f"✗ First Q26 bar is {first_q26}, expected {EXPECTED_FIRST_Q26}.")

    meta = store.save_bars(SYMBOL, NEW_CONTRACT, q26)
    logger.info(f"Q26 saved. Dataset now: {meta['start_date']} → {meta['end_date']} ({meta['bar_count_1m']} bars)")
    logger.info(f"Segments: {json.dumps(meta['contract_segments'], indent=2)}")

    logger.info("=" * 64)
    logger.info("MCL contract switch complete.")
    logger.info('IMPORTANT: update SYMBOL_CONTRACTS["MCL"] = "CON.F.US.MCLE.Q26" in src/data/market_store.py')
    logger.info("=" * 64)
    return 0


if __name__ == "__main__":
    sys.exit(main())
