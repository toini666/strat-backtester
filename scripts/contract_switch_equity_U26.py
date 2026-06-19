#!/usr/bin/env python3
"""
One-time script: Quarterly equity-index roll M26 → U26 for MNQ, MES, MYM.

Context:
  - Local data for all three was last updated to 2026-05-29 ~07:40 Brussels, all
    on the M26 (June) contract.
  - Front month rolls to U26 (September) from the CME Sunday reopen on
    2026-06-14 18:00 ET = 2026-06-14 22:00 UTC = 2026-06-15 00:00 Brussels (CEST).
    The user designates Monday 2026-06-15 00:00 Brussels as the switch point.
  - Equity index futures close Fri 17:00 ET (23:00 Brussels) and reopen Sun
    18:00 ET (Mon 00:00 Brussels). The weekend gap means M26 has NO bars between
    Friday close and the Sunday reopen where U26 takes over — so the OLD fetch is
    naturally protected: ending the M26 fill on Saturday returns the Friday close
    cleanly and grabs no Sunday-evening M26 bars (those belong to U26).
  - U26 carries a roll premium/discount vs M26, so the first U26 bar opens at a
    visibly different price than M26's last close. This is expected — log it for a
    manual TradingView eyeball, do NOT hard-fail on the price jump.

Per symbol:
  1. Fetch remaining M26 bars (overlap from ~2026-05-28 → 2026-06-13 Sat), save as
     M26 (same contract: pure append, no roll).
  2. Fetch U26 bars (2026-06-14 22:00 UTC = 2026-06-15 00:00 Brussels → now),
     save as U26 (triggers the roll in save_bars: new contract segment).
  3. Verify last M26 bar is Fri 2026-06-12 and first U26 bar is Mon 2026-06-15 00:00.

After running, update SYMBOL_CONTRACTS in src/data/market_store.py:
    "MNQ": "CON.F.US.MNQ.U26"
    "MES": "CON.F.US.MES.U26"
    "MYM": "CON.F.US.MYM.U26"
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

SYMBOLS = ["MNQ", "MES", "MYM"]

def old_contract(sym: str) -> str:
    return f"CON.F.US.{sym}.M26"

def new_contract(sym: str) -> str:
    return f"CON.F.US.{sym}.U26"

# M26 fill window: small overlap back into existing data → Saturday (returns Fri close).
M26_START_UTC = datetime(2026, 5, 28, 0, 0, 0)    # safe overlap with existing data
M26_END_UTC   = datetime(2026, 6, 13, 0, 0, 0)    # Sat 13/06 — no trading, returns Fri 12/06 close

# U26 fetch window: Sunday CME reopen → now.
U26_START_UTC = datetime(2026, 6, 14, 22, 0, 0)   # = 2026-06-15 00:00 Brussels (CEST), Mon session open
U26_END_UTC   = datetime.utcnow()

EXPECTED_FIRST_U26 = pd.Timestamp("2026-06-15 00:00", tz=BRUSSELS_TZ)


def switch_symbol(client: TopstepClient, store: MarketDataStore, sym: str) -> bool:
    old_cid = old_contract(sym)
    new_cid = new_contract(sym)

    logger.info("=" * 64)
    logger.info(f"[{sym}] Step 1: fill {old_cid} ({M26_START_UTC} → {M26_END_UTC} UTC)")
    logger.info("=" * 64)

    m26 = client.fetch_historical_data(
        contract_id=old_cid, start=M26_START_UTC, end=M26_END_UTC,
        timeframe="1m", live=False,
    )
    if m26.empty:
        logger.error(f"[{sym}] No M26 data returned — cannot fill May29→Jun12 gap. "
                     f"ABORTING this symbol to avoid a silent 3-week hole before U26.")
        return False

    last_m26 = m26.index.max()
    logger.info(f"[{sym}] Fetched {len(m26)} M26 bars: {m26.index.min()} → {last_m26}")
    if last_m26.date() != pd.Timestamp("2026-06-12").date():
        logger.warning(f"[{sym}] last M26 bar is {last_m26} — expected Friday 2026-06-12. Check before trusting.")
    meta = store.save_bars(sym, old_cid, m26)
    logger.info(f"[{sym}] M26 saved. Dataset now: {meta['start_date']} → {meta['end_date']} ({meta['bar_count_1m']} bars)")

    logger.info("=" * 64)
    logger.info(f"[{sym}] Step 2: fetch {new_cid} ({U26_START_UTC} UTC = 2026-06-15 00:00 Brussels → now)")
    logger.info("=" * 64)

    u26 = client.fetch_historical_data(
        contract_id=new_cid, start=U26_START_UTC, end=U26_END_UTC,
        timeframe="1m", live=False,
    )
    if u26.empty:
        logger.error(f"[{sym}] No U26 data returned — contract ID '{new_cid}' may be wrong. NOT saving.")
        return False

    first_u26 = u26.index.min()
    logger.info(f"[{sym}] Fetched {len(u26)} U26 bars: {first_u26} → {u26.index.max()}")
    logger.info(f"[{sym}] First 5 U26 bars (Brussels) — eyeball vs TradingView (roll premium expected):")
    for ts, row in u26.head(5).iterrows():
        logger.info(f"    {ts}  O={row['Open']}  H={row['High']}  L={row['Low']}  C={row['Close']}")

    if first_u26 == EXPECTED_FIRST_U26:
        logger.info(f"[{sym}] ✓ First U26 bar is exactly {first_u26} (Mon 2026-06-15 00:00 Brussels).")
    else:
        logger.warning(f"[{sym}] ✗ First U26 bar is {first_u26}, expected {EXPECTED_FIRST_U26}.")

    meta = store.save_bars(sym, new_cid, u26)
    logger.info(f"[{sym}] U26 saved. Dataset now: {meta['start_date']} → {meta['end_date']} ({meta['bar_count_1m']} bars)")
    logger.info(f"[{sym}] Segments: {json.dumps(meta['contract_segments'])}")
    return True


def main():
    client = TopstepClient()
    store = MarketDataStore()
    results = {}
    for sym in SYMBOLS:
        try:
            results[sym] = switch_symbol(client, store, sym)
        except Exception as e:
            logger.exception(f"[{sym}] failed: {e}")
            results[sym] = False

    logger.info("=" * 64)
    logger.info("EQUITY ROLL SUMMARY (M26 → U26)")
    for sym, ok in results.items():
        logger.info(f"  {sym}: {'OK' if ok else 'FAILED'}")
    logger.info("IMPORTANT: update SYMBOL_CONTRACTS in src/data/market_store.py to U26 for MNQ/MES/MYM.")
    logger.info("=" * 64)
    return 0 if all(results.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
