#!/usr/bin/env python3
"""
Fix script: MBT contract switch was on 2026-03-24 at 23:00 Brussels (not March 26).

Problem:
  - Current 1m CSV has H26 prices from 2026-03-24 23:00 Brussels onwards (wrong)
  - The real switch to J26 happened on 2026-03-24 at 23:00 Brussels (22:00 UTC)
  - Verified: J26 bar at 2026-03-24 22:00 UTC has Open=70650, Close=70535 ✓

Fix:
  1. Truncate existing 1m data to keep only bars up to 2026-03-24 21:59 Brussels
  2. Fetch J26 bars from 2026-03-24 22:00 UTC to now
  3. Merge, save, recompose all timeframes
  4. Update index: H26 ends 2026-03-24, J26 starts 2026-03-24
"""
import sys
import os
import logging
import json
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from dotenv import load_dotenv
load_dotenv()

import pandas as pd
from src.data.topstep import TopstepClient
from src.data.market_store import MarketDataStore
from src.data.recompose import recompose_bars

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger(__name__)

SYMBOL = "MBT"
OLD_CONTRACT = "CON.F.US.MBT.H26"
NEW_CONTRACT = "CON.F.US.MBT.J26"
BRUSSELS_TZ = "Europe/Brussels"

# Cut point: last correct H26 bar is 2026-03-24 21:59 Brussels (CET=UTC+1)
# Everything from 2026-03-24 22:00 UTC (= 23:00 Brussels) onwards is J26
H26_CUTOFF_BRUSSELS = pd.Timestamp("2026-03-24 21:59:00+01:00")

# J26 start: 2026-03-24 22:00 UTC = 23:00 Brussels (CME open)
J26_START_UTC = datetime(2026, 3, 24, 22, 0, 0)
J26_END_UTC = datetime.utcnow()

DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data', 'market_data'))
RECOMPOSE_TIMEFRAMES = ["2m", "3m", "5m", "7m", "15m"]


def main():
    store = MarketDataStore()
    symbol_dir = os.path.join(DATA_DIR, SYMBOL)
    csv_1m_path = os.path.join(symbol_dir, f"{SYMBOL}_1m.csv")

    # ---- Step 1: Truncate existing 1m data ----
    logger.info("=" * 60)
    logger.info(f"Step 1: Truncating existing data to {H26_CUTOFF_BRUSSELS}")
    logger.info("=" * 60)

    df_existing = pd.read_csv(csv_1m_path, index_col="Date")
    df_existing.index = pd.to_datetime(df_existing.index, utc=True)
    df_existing.index = df_existing.index.tz_convert(BRUSSELS_TZ)
    df_existing.sort_index(inplace=True)

    logger.info(f"Existing data: {df_existing.index.min()} → {df_existing.index.max()} ({len(df_existing)} bars)")

    df_h26 = df_existing[df_existing.index <= H26_CUTOFF_BRUSSELS]
    logger.info(f"After truncation: {df_h26.index.min()} → {df_h26.index.max()} ({len(df_h26)} bars)")
    logger.info(f"Removed {len(df_existing) - len(df_h26)} incorrect bars")

    # ---- Step 2: Fetch J26 data ----
    logger.info("=" * 60)
    logger.info(f"Step 2: Fetching {NEW_CONTRACT} from {J26_START_UTC} UTC to now")
    logger.info("=" * 60)

    client = TopstepClient()
    j26_data = client.fetch_historical_data(
        contract_id=NEW_CONTRACT,
        start=J26_START_UTC,
        end=J26_END_UTC,
        timeframe="1m",
        live=False,
    )

    if j26_data.empty:
        logger.error("No J26 data returned!")
        return 1

    logger.info(f"Fetched {len(j26_data)} J26 bars: {j26_data.index.min()} → {j26_data.index.max()}")

    # Convert J26 to Brussels tz
    j26_data.index = j26_data.index.tz_convert(BRUSSELS_TZ)

    # ---- Step 3: Merge H26 (truncated) + J26 ----
    logger.info("=" * 60)
    logger.info("Step 3: Merging and saving")
    logger.info("=" * 60)

    df_merged = pd.concat([df_h26, j26_data])
    df_merged = df_merged[~df_merged.index.duplicated(keep="last")]
    df_merged.sort_index(inplace=True)

    logger.info(f"Merged: {df_merged.index.min()} → {df_merged.index.max()} ({len(df_merged)} bars)")

    # Verify gap at switch point
    switch_area = df_merged["2026-03-24 21:50":"2026-03-24 23:10"]
    logger.info(f"Switch area preview:")
    logger.info(switch_area.to_string())

    # Save 1m CSV
    df_merged.to_csv(csv_1m_path, index_label="Date")
    logger.info(f"Saved {len(df_merged)} 1m bars to {csv_1m_path}")

    # ---- Step 4: Recompose all timeframes ----
    for tf in RECOMPOSE_TIMEFRAMES:
        df_tf = recompose_bars(df_merged, tf)
        tf_path = os.path.join(symbol_dir, f"{SYMBOL}_{tf}.csv")
        df_tf.to_csv(tf_path, index_label="Date")
        logger.info(f"Generated {SYMBOL}_{tf}.csv: {len(df_tf)} bars")

    # ---- Step 5: Update index.json ----
    total_size = sum(
        os.path.getsize(os.path.join(symbol_dir, f))
        for f in os.listdir(symbol_dir) if f.endswith(".csv")
    )
    total_size_mb = round(total_size / (1024 * 1024), 2)

    index_path = os.path.join(DATA_DIR, "index.json")
    with open(index_path, "r") as f:
        index = json.load(f)

    for entry in index:
        if entry.get("symbol") == SYMBOL:
            entry["contract_id"] = NEW_CONTRACT
            entry["start_date"] = str(df_merged.index.min())
            entry["end_date"] = str(df_merged.index.max())
            entry["bar_count_1m"] = len(df_merged)
            entry["total_size_mb"] = total_size_mb
            entry["updated_at"] = datetime.utcnow().isoformat()

            # Rebuild contract segments with correct switch date
            h26_end_date = str(df_h26.index.max().date())
            j26_start_date = str(j26_data.index.min().date())
            j26_end_date = str(df_merged.index.max().date())

            existing_segments = entry.get("contract_segments", [])
            # Keep all segments up to (and including) H26, update H26 end date, add J26
            new_segments = []
            for seg in existing_segments:
                if seg["contract"] == OLD_CONTRACT:
                    seg["to"] = h26_end_date
                    new_segments.append(seg)
                    break
                new_segments.append(seg)

            new_segments.append({
                "contract": NEW_CONTRACT,
                "label": "J26",
                "from": j26_start_date,
                "to": j26_end_date,
            })
            entry["contract_segments"] = new_segments
            break

    with open(index_path, "w") as f:
        json.dump(index, f, indent=2, default=str)
    logger.info("Updated index.json")

    logger.info("=" * 60)
    logger.info("Fix complete!")
    logger.info(f"MBT data now: H26 up to {H26_CUTOFF_BRUSSELS.date()}, J26 from 2026-03-24 onwards")
    logger.info("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
