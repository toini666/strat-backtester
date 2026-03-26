# CLAUDE.md — Nebular Apollo Backtesting Engine

## Project Overview

Nebular Apollo is a quantitative backtesting engine for futures trading strategies. It backtests algorithmic strategies on historical 1-minute OHLCV data, with higher-timeframe bar recomposition, an event-driven simulator for complex position management, and a React frontend for visualization.

**Key technical constraint**: All indicator computations must match TradingView PineScript indicators exactly. Strategies are translated from PineScript and the backtester must produce trades identical to what TradingView shows.

## Quick Start

```bash
# Backend
cd /Users/awagon/Documents/dev/nebular-apollo
source venv/bin/activate
uvicorn backend.main:app --reload --port 8001

# Frontend (separate terminal)
cd frontend && npm run dev

# Tests
pytest -xvs
```

## Architecture

```
Frontend (React/Vite :5173) → HTTP → Backend (FastAPI :8001)
                                         │
                    ┌────────────────────┼────────────────────┐
                    ▼                    ▼                    ▼
            Data Layer           Strategy Engine        Backtest Engine
         market_store.py         strategies/*.py        simulator.py
         recompose.py            base.py (ABC)          (Event-driven)
         topstep.py              ema_break_osc.py
                                 ema9_scalp.py
                                 utbot_alligator_st.py
```

## Backtest Engine — Event-Driven Simulator (`src/engine/simulator.py`)

All strategies use the event-driven simulator. It processes bars sequentially with intra-bar 1-minute resolution. The simulator provides building blocks that strategies can use or not:
- **Partial take-profit** (optional): TP1 closes `tp1_partial_pct` of position at a price level. TP2 closes `tp2_partial_pct` on a secondary condition (e.g. EMA cross). Strategies control whether they use 0, 1, or 2 partial TPs, and what conditions trigger them.
- **Breakeven** (optional): Can move stop loss to entry price after TP1. Strategies can also trigger breakeven on other conditions.
- **Intra-bar resolution**: When a bar's range spans both SL and TP1, zooms into 1-minute data to determine which was hit first
- **TP1 execution modes**: `"touch"` (immediate) or `"bar_close_if_touched"` (deferred to bar close)
- **Auto-close**: Closes open positions at a configured time (default 22:00 reference Brussels time)
- **Blackout windows**: Prevents new entries during configured time slots
- **Cooldown**: Minimum bars between trade close and next entry

The exit logic is strategy-agnostic: the simulator handles SL/TP1 touch, bar-close-if-touched TP1, EMA-cross TP2, optional fixed TP2 prices, optional Supertrend trailing SL, and optional pre-TP1 breakeven levels — all driven by keys returned from `generate_signals()`.

## Active Strategies

All strategies have corresponding PineScript files in `Pinescripts/`:

| Strategy | File | PineScript | Warmup Bars |
|----------|------|-----------|-------------|
| EMABreakOsc | `ema_break_osc.py` | `EMA-Break-Osc.txt` | 250 |
| EMA9Scalp | `ema9_scalp.py` | `EMA9-scalp.txt` | 80 |
| UTBotAlligatorST | `utbot_alligator_st.py` | `UTBot-Alligator-ST.txt` | 120 |

## Data Flow

### 1. Data Loading
All data comes from local CSV files via `market_store.py`. The store holds 1-minute OHLCV bars per symbol (MNQ, MES, MGC, etc.).

**Data sources:**
- **Historical backfill**: Databento OHLCV-1m CSVs (one-time import per ticker). Requires front-month contract resolution from multi-contract data. See agent memory for full import procedure.
- **Ongoing updates**: Topstep API via `save_bars()`, which handles merge, timezone conversion, and timeframe recomposition automatically.

### Contract Switches (Rollovers)

When a futures contract expires and the front-month rolls to the next contract:

1. **Write a one-time script** (see `scripts/contract_switch_MBT_J26.py` as template) that:
   - Fetches the remaining bars for the **old contract** (from last known bar to the day before the switch closes)
   - Saves with `save_bars(symbol, OLD_CONTRACT_ID, data)` — appends to existing data, same contract
   - Fetches bars for the **new contract** starting from the **first bar of the new session** (CME open = 17:00 EDT = 22:00 UTC when Brussels is CET/UTC+1, or 21:00 UTC when Brussels is CEST/UTC+2)
   - Saves with `save_bars(symbol, NEW_CONTRACT_ID, data)` — `save_bars` detects the contract change, appends only bars after `existing_end`, and adds a new segment to `contract_segments`

2. **Update `SYMBOL_CONTRACTS`** in `src/data/market_store.py` to point to the new contract ID.

3. **CME month codes**: F=Jan, G=Feb, H=Mar, J=Apr, K=May, M=Jun, N=Jul, Q=Aug, U=Sep, V=Oct, X=Nov, Z=Dec

**Time reference for contract switch dates:**
- Brussels UTC offset: CET=UTC+1 (Oct→last Sunday March), CEST=UTC+2 (last Sunday March→Oct)
- US EDT/EST offset: EDT=UTC-4 (2nd Sunday Mar→1st Sunday Nov), EST=UTC-5
- CME opens at 17:00 EDT / 18:00 EST = 22:00 UTC (summer, Brussels CEST) or 22:00 UTC (winter, Brussels CET)
- The gap between the last H26 bar and first J26 bar is the inter-session gap (e.g., 21:58 Brussels → 23:00 Brussels)

**CSV format**: `Date,Open,High,Low,Close,Volume` with `Date` as Brussels tz-aware timestamps. CSVs may contain mixed UTC offsets (+01:00 winter / +02:00 summer) — `market_store.py` reads them via `pd.to_datetime(utc=True)` then `tz_convert('Europe/Brussels')`.

### 2. Timeframe Recomposition (`src/data/recompose.py`)
Higher-timeframe bars (3m, 5m, 7m, 15m, etc.) are recomposed from 1-minute data:
- Bars re-anchor at each **session start** (detected via gaps > 30 minutes in the 1m data)
- Incomplete bars at session start are dropped; partial bars at session end are kept
- This matches TradingView's bar formation behavior

### 3. Warmup Buffer
Indicators need historical data before the backtest start date. The warmup is calculated per-strategy:
```python
STRATEGY_WARMUP_BARS = {
    "EMABreakOsc": 250,     # EMA(30)→100 + MFI(35)+cloud(35)→112 + margin
    "EMA9Scalp": 80,        # EMA(7)→28 + setup detection margin
    "UTBotAlligatorST": 120, # SMMA(13)+offset(8)→~60 + ATR(10) + margin
}
```
The buffer is converted to calendar days with weekend awareness:
```python
trading_minutes_needed = warmup_bars * minutes_per_bar
trading_days = trading_minutes_needed / (23 * 60)
calendar_days = max(2, int(trading_days * 7 / 5) + 3)
```

### 4. Signal Generation
Each strategy's `generate_signals()` returns a dict with required and optional keys:

**Required:**
- `long_entries`, `short_entries`: boolean Series
- `sl_long`, `sl_short`, `tp1_long`, `tp1_short`: float Series (price levels)
- `ema_main`, `ema_secondary`: Series (for EMA-cross exit logic)

**Optional (simulator handles via `.get()`):**
- `be_long`, `be_short`: float Series — custom breakeven price levels (EMA9Scalp)
- `entry_price_long`, `entry_price_short`: float Series — override bar-close entry price (UTBotAlligatorST)
- `tp2_long`, `tp2_short`: float Series — fixed TP2 price levels (UTBotAlligatorST)
- `supertrend`, `supertrend_trend`: Series — Supertrend trailing SL (UTBotAlligatorST)
- `cooldown_bars`: int — per-signal cooldown override
- `debug_frame`: DataFrame — all indicator values for CSV export

### 5. Simulation
The simulator processes each timeframe bar sequentially. For each bar:
1. Check auto-close
2. Process exits (SL, TP1, breakeven) — with intra-bar 1m resolution if ambiguous
3. Process close-based exits (TP2 EMA cross, EMA cross for final close)
4. Process entries (if no blackout, no cooldown, no position open)

## DST-Aware Sessions and Time Handling

**Critical**: All time-based logic (sessions, blackout windows, auto-close) is DST-aware.

### The Problem
CME futures follow US/Eastern time. Brussels and US/Eastern are normally 6h apart, but during DST transition periods (~3 weeks in March, ~1 week in Oct/Nov), the offset drops to 5h. This shifts all market times by -1h in Brussels.

### The Solution
All configured times (session boundaries, blackout windows, auto-close) are in **reference Brussels time** (= when Brussels-ET = 6h). The system auto-detects the offset:

```python
def _get_market_hour_offset(ts):
    # Compare Brussels vs US/Eastern UTC offsets
    # diff=6 → offset=0 (standard), diff=5 → offset=-1 (shifted)
```

Wall-clock Brussels time is normalized to the reference frame via `_to_ref_minutes()` before any comparison. This means:
- **No manual adjustment needed** when backtesting across DST transitions
- Blackout windows, session labels, and auto-close all shift automatically

### Session Definitions (Reference Brussels Time)
| Session | Reference Hours |
|---------|----------------|
| Asia    | 00:00 – 08:59  |
| UK      | 09:00 – 15:29  |
| US      | 15:30 – end    |

There is **no "Outside" session** — all times map to Asia/UK/US. Blackout windows handle any periods where entries should be blocked.

### Default Blackout Windows (Reference Brussels Time)
Configured in `BacktestEngineSettings`. Users see/edit these in the frontend sidebar. The system auto-adjusts for DST.

## Strategy Implementation Guide

### Adding a New Strategy

1. Create `src/strategies/my_strategy.py`
2. Inherit from `Strategy`, set `use_simulator = True`
3. Set class attributes and implement `generate_signals()`
4. The strategy is auto-discovered at startup (no registration needed)
5. Add warmup value to `STRATEGY_WARMUP_BARS` in `backend/api.py`
6. Add corresponding PineScript file in `Pinescripts/`

```python
from .base import Strategy
import pandas as pd
import numpy as np

class MyStrategy(Strategy):
    name = "MyStrategy"
    default_params = {"ema_len": 20, "threshold": 0.5}
    param_ranges = {"ema_len": [10, 20, 30], "threshold": [0.3, 0.5, 0.7]}

    use_simulator = True
    simulator_settings = {
        "tp1_execution_mode": "bar_close_if_touched",
    }

    def generate_signals(self, data, params=None):
        p = self.get_params(params)
        # ... compute indicators and signals ...
        return {
            "long_entries": long_entries,    # bool Series
            "short_entries": short_entries,  # bool Series
            "sl_long": sl_long,             # float Series (price)
            "sl_short": sl_short,           # float Series (price)
            "tp1_long": tp1_long,           # float Series (price)
            "tp1_short": tp1_short,         # float Series (price)
            "ema_main": ema_main,           # Series (for exit logic)
            "ema_secondary": ema_secondary, # Series (for TP2 EMA cross)
            "cooldown_bars": int,           # Optional: per-signal cooldown
            "debug_frame": debug_df,        # Optional DataFrame
            # Optional additional keys (simulator handles via .get()):
            # "be_long", "be_short"                       — custom breakeven levels
            # "entry_price_long", "entry_price_short"     — override entry price
            # "tp2_long", "tp2_short"                     — fixed TP2 price levels
            # "supertrend", "supertrend_trend"            — Supertrend trailing SL
        }

    # For configurable TP partial sizes:
    def get_simulator_settings(self, params=None):
        p = self.get_params(params)
        settings = self.simulator_settings.copy()
        settings["tp1_partial_pct"] = p.get("tp1_partial_pct", 0.25)
        settings["tp2_partial_pct"] = p.get("tp2_partial_pct", 0.25)
        return settings
```

### Critical: Matching PineScript Indicators

When translating from PineScript:
- **EMA**: Use `pd.Series.ewm(span=n, adjust=False).mean()` — this matches Pine's recursive `ta.ema()`
- **SMA**: Use `pd.Series.rolling(n).mean()`
- **LinReg**: Use `ta.linreg()` from pandas-ta (local lib in `libs/pandas-ta/`)
- **MFI**: Custom implementation — Pine uses `hl2` as source (not `hlc3`), centered at 0
- **Convergence**: EMA(n) needs ~4n bars after first valid value for 99% convergence. Account for this in warmup.
- **Session boundaries**: Data gaps between sessions cause resampling anchors to reset. The recompose module handles this.

## Position Sizing

```
Risk Amount = Equity × Risk Per Trade (e.g. 1%)
SL Ticks    = |Entry - SL| / Tick Size
Contracts   = floor(Risk Amount / (SL Ticks × Tick Value))
```

Partial exits use the **initial** contract count (not remaining):
- TP1: `floor(initial_size × tp1_partial_pct)` contracts
- TP2: `floor(initial_size × tp2_partial_pct)` contracts
- Remainder closes at final exit (EMA cross, auto-close, or end of data)

Example: 9 contracts with 25%/25% → 2 at TP1, 2 at TP2, 5 at final close.

## Key Files

| File | Purpose |
|------|---------|
| `backend/api.py` | FastAPI endpoints, backtest orchestration, warmup calculation |
| `backend/main.py` | App entry, CORS, route mounting |
| `backend/market_data_routes.py` | Market data CRUD endpoints |
| `src/engine/simulator.py` | Event-driven simulator with partial TP and intra-bar resolution |
| `src/data/recompose.py` | Timeframe recomposition from 1m bars |
| `src/data/market_store.py` | Local market data storage (CSV) |
| `src/strategies/base.py` | Abstract Strategy class |
| `src/strategies/ema_break_osc.py` | EMA Break + Oscillator strategy |
| `src/strategies/ema9_scalp.py` | EMA9 Scalp strategy |
| `src/strategies/utbot_alligator_st.py` | UTBot Alligator SuperTrend strategy |
| `src/optimizer/parameter_optimizer.py` | Grid search with session combinations (legacy, to be refactored) |
| `frontend/src/App.tsx` | React app root, state management |
| `frontend/src/api.ts` | API client, types, defaults |
| `frontend/src/components/Sidebar.tsx` | Backtest configuration UI |
| `frontend/src/components/Dashboard.tsx` | Results display, session filters |

## Contract Specifications

Defined in `CONTRACT_SPECS` and `FEES_MAP` dicts in `backend/api.py`:

| Symbol | Tick Size | Tick Value | Point Value | Fee RT |
|--------|-----------|------------|-------------|--------|
| M2K    | 0.10      | $0.50      | $5.00       | $0.74  |
| MBT    | 5.00      | $0.50      | $0.10       | $2.34  |
| MCL    | 0.01      | $1.00      | $100.00     | $1.04  |
| MES    | 0.25      | $1.25      | $5.00       | $0.74  |
| MGC    | 0.10      | $1.00      | $10.00      | $1.24  |
| MNQ    | 0.25      | $0.50      | $2.00       | $0.74  |
| MYM    | 1.00      | $0.50      | $0.50       | $0.74  |


## Testing

```bash
pytest -xvs                          # All tests
pytest tests/test_simulator.py -xvs  # Simulator tests
pytest tests/test_api.py -xvs        # API + session tests
pytest tests/test_recompose.py -xvs  # Recomposition tests
```

Key test areas:
- Blackout window blocking
- TP1 touch vs bar-close-if-touched execution
- Partial exit sizing (25% default)
- Auto-close at configured time
- DST-shifted session classification
- Timeframe recomposition with session gaps

## Important Conventions

1. **All times in Brussels timezone** — data is stored/indexed in UTC but all business logic converts to `Europe/Brussels`
2. **Reference frame for configured times** — blackout, auto-close, session boundaries use "reference" Brussels time (offset=0). The system auto-adjusts for DST misalignment.
3. **No "Outside" session** — removed. All bars are Asia, UK, or US.
4. **Warmup is not backtest data** — warmup bars are loaded before the requested start date and discarded after indicator computation. Debug exports only contain the backtest range.
5. **Strategy auto-discovery** — any `Strategy` subclass in `src/strategies/` is automatically registered at startup.
6. **pandas-ta is local** — the library lives in `libs/pandas-ta/`, not installed via pip.
7. **All strategies use the event-driven simulator** — there is no legacy VectorBT path for backtesting. The optimization module still uses VectorBT and is pending refactoring.
