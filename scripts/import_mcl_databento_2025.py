"""
Import Databento MCL historical data (Jan 2025 – Jan 2026) into the market data store.

- Filters outright contracts only (no spreads)
- Resolves front-month per day using daily volume dominance (matches CME rollover behaviour)
- Prepends strictly before the existing data start (2026-01-15 18:49 UTC)
- Does NOT overwrite any existing data
- Rebuilds all recomposed timeframes after save
"""

import sys
from pathlib import Path

# Project root on sys.path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import json
import pandas as pd
from src.data.market_store import MarketDataStore

SYMBOL = "MCL"
DATABENTO_CSV = ROOT / "data/GLBX-20260329-R78MDTALN4/glbx-mdp3-20250101-20260131.ohlcv-1m.csv"
MCL_1M_CSV = ROOT / "data/market_data/MCL/MCL_1m.csv"

# The main front-month contract candidates for the period (Jan 2025 – Jan 2026).
# Far-out back months (J6, K6, etc.) are excluded — negligible volume, never front-month.
MAIN_CONTRACTS = [
    "MCLG5",  # Feb 2025
    "MCLH5",  # Mar 2025
    "MCLJ5",  # Apr 2025
    "MCLK5",  # May 2025
    "MCLM5",  # Jun 2025
    "MCLN5",  # Jul 2025
    "MCLQ5",  # Aug 2025
    "MCLU5",  # Sep 2025
    "MCLV5",  # Oct 2025
    "MCLX5",  # Nov 2025
    "MCLZ5",  # Dec 2025
    "MCLF6",  # Jan 2026
    "MCLG6",  # Feb 2026
    "MCLH6",  # Mar 2026 (may be front-month by Jan 15 2026)
]

# ── 1. Load Databento CSV ─────────────────────────────────────────────────────

print("Loading Databento CSV …")
db = pd.read_csv(DATABENTO_CSV)
print(f"  Total rows (all symbols): {len(db):,}")

# ── 2. Filter to outright contracts only ─────────────────────────────────────

outright = db[~db["symbol"].str.contains("-")].copy()
outright = outright[outright["symbol"].isin(MAIN_CONTRACTS)].copy()
print(f"  Rows after outright + main-contract filter: {len(outright):,}")

# ── 3. Parse timestamps ───────────────────────────────────────────────────────

outright["ts"] = pd.to_datetime(outright["ts_event"], utc=True)
outright["date"] = outright["ts"].dt.date

# ── 4. Resolve daily dominant contract (highest total volume per day) ─────────

daily_vol = outright.groupby(["date", "symbol"])["volume"].sum().unstack(fill_value=0)
dominant = daily_vol.idxmax(axis=1).to_dict()

print("\nRollover schedule (daily dominant contract):")
prev_sym = None
for d, sym in sorted(dominant.items()):
    if sym != prev_sym:
        print(f"  {d}: → {sym}")
        prev_sym = sym

outright["dominant"] = outright["date"].map(dominant)
front = outright[outright["symbol"] == outright["dominant"]].copy()
front = front.set_index("ts").sort_index()

# ── 5. Sanity check: no duplicate timestamps ──────────────────────────────────

dupes = front.index.duplicated().sum()
assert dupes == 0, f"Found {dupes} duplicate timestamps — check rollover logic!"
print(f"\n  No duplicate timestamps ✓")

# ── 6. Convert to Brussels timezone ──────────────────────────────────────────

front.index = front.index.tz_convert("Europe/Brussels")

# ── 7. Determine cut-off: strictly before existing data start ─────────────────

ours_head = pd.read_csv(MCL_1M_CSV, index_col="Date", nrows=1)
ours_head.index = pd.to_datetime(ours_head.index, utc=True).tz_convert("Europe/Brussels")
our_start = ours_head.index.min()
print(f"\n  Existing data starts at: {our_start}")

databento_part = front[front.index < our_start]
print(f"  Databento bars to prepend: {len(databento_part):,}")
print(f"  Databento period: {databento_part.index.min()} → {databento_part.index.max()}")

# ── 8. Price alignment check at the junction ─────────────────────────────────

last_db = databento_part.iloc[-1]
ours_full = pd.read_csv(MCL_1M_CSV, index_col="Date")
ours_full.index = pd.to_datetime(ours_full.index, utc=True).tz_convert("Europe/Brussels")
first_ours = ours_full.iloc[0]

print(f"\n  Junction check:")
print(f"    Last Databento bar:  {databento_part.index[-1]}  close={last_db['close']:.2f}  vol={int(last_db['volume'])}")
print(f"    First existing bar:  {ours_full.index[0]}  close={first_ours['Close']:.2f}  vol={int(first_ours['Volume'])}")

# ── 9. Build new_part with correct column names ───────────────────────────────

new_part = databento_part[["open", "high", "low", "close", "volume"]].rename(
    columns={"open": "Open", "high": "High", "low": "Low", "close": "Close", "volume": "Volume"}
)
new_part.index.name = "Date"
new_part["Volume"] = new_part["Volume"].astype(int)

# ── 10. Concatenate and save ──────────────────────────────────────────────────

combined = pd.concat([new_part, ours_full]).sort_index()
dupes = combined.index.duplicated(keep="last").sum()
if dupes:
    print(f"  Warning: {dupes} duplicate timestamps removed (kept last)")
    combined = combined[~combined.index.duplicated(keep="last")]

print(f"\n  Combined bars: {len(combined):,}")
print(f"  Combined period: {combined.index.min()} → {combined.index.max()}")

combined.to_csv(MCL_1M_CSV, index_label="Date")
print(f"\n  Saved {MCL_1M_CSV}")

# ── 11. Update index.json ─────────────────────────────────────────────────────

INDEX_PATH = ROOT / "data/market_data/index.json"
with open(INDEX_PATH) as f:
    index = json.load(f)

for entry in index:
    if entry.get("symbol") == SYMBOL:
        # Add a new segment for the Databento backfill (multiple contracts)
        # Build per-contract segments from the rollover schedule
        db_segments = []
        prev_sym2 = None
        seg_start = None
        our_start_date = our_start.date()
        for d, sym in sorted(dominant.items()):
            d_ts = pd.Timestamp(d)
            if d >= our_start_date:
                break
            if sym != prev_sym2:
                if prev_sym2 is not None:
                    db_segments.append({
                        "contract": f"DATABENTO:{prev_sym2}",
                        "label": prev_sym2,
                        "from": str(seg_start),
                        "to": str(d_ts.date()),
                    })
                prev_sym2 = sym
                seg_start = d_ts.date()

        if prev_sym2 is not None:
            db_segments.append({
                "contract": f"DATABENTO:{prev_sym2}",
                "label": prev_sym2,
                "from": str(seg_start),
                "to": str(combined.index.min().date()),
            })

        # Prepend Databento segments before existing segments
        existing_segments = entry.get("contract_segments", [])
        entry["contract_segments"] = db_segments + existing_segments
        entry["start_date"] = str(combined.index.min())
        entry["bar_count_1m"] = len(combined)

        # Recalculate total_size_mb
        symbol_dir = ROOT / "data/market_data" / SYMBOL
        total_size = sum(f.stat().st_size for f in symbol_dir.glob("*.csv"))
        entry["total_size_mb"] = round(total_size / (1024 * 1024), 2)

        break

with open(INDEX_PATH, "w") as f:
    json.dump(index, f, indent=2, default=str)
print("  Updated index.json")

# ── 12. Rebuild recomposed timeframes ─────────────────────────────────────────

print("\nRebuilding recomposed timeframes …")
store = MarketDataStore()
store.rebuild_recomposed_data([SYMBOL])
print("Done.")
