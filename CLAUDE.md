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
         market_store.py         strategies/*.py      ┌──────────────┐
         recompose.py            base.py (ABC)        │ backtester.py│ (VectorBT, legacy)
         topstep.py              ema_break_osc.py     │ simulator.py │ (Event-driven, new)
         yfinance_provider.py    rob_reversal.py      └──────────────┘
                                 delta_div.py
                                 utbot_stc.py ...
```

## Two Backtest Engines

### 1. VectorBT Engine (`src/engine/backtester.py`) — Legacy
Used by most strategies. Vectorized, fast, but limited:
- No partial take-profit
- No intra-bar resolution (can't determine which level was hit first within a bar)
- No breakeven moves after TP1

### 2. Event-Driven Simulator (`src/engine/simulator.py`) — New
Used by strategies with `use_simulator = True` (currently: EMABreakOsc). Processes bars sequentially with intra-bar 1-minute resolution. The simulator provides building blocks that strategies can use or not:
- **Partial take-profit** (optional): TP1 closes `tp1_partial_pct` of position at a price level. TP2 closes `tp2_partial_pct` on a secondary condition (e.g. EMA cross). Strategies control whether they use 0, 1, or 2 partial TPs, and what conditions trigger them.
- **Breakeven** (optional): Can move stop loss to entry price after TP1. Strategies can also trigger breakeven on other conditions.
- **Intra-bar resolution**: When a bar's range spans both SL and TP1, zooms into 1-minute data to determine which was hit first
- **TP1 execution modes**: `"touch"` (immediate) or `"bar_close_if_touched"` (deferred to bar close)
- **Auto-close**: Closes open positions at a configured time (default 22:00 reference Brussels time)
- **Blackout windows**: Prevents new entries during configured time slots
- **Cooldown**: Minimum bars between trade close and next entry

The exit logic (TP conditions, breakeven rules, EMA crosses) will vary per strategy. The simulator currently has EMABreakOsc-specific exit logic hardcoded. As more strategies are added, this should be refactored into strategy-provided exit callbacks.

### Choosing an Engine
A strategy opts into the simulator by setting class attributes:
```python
class MyStrategy(Strategy):
    use_simulator = True
    simulator_settings = {
        "tp1_execution_mode": "bar_close_if_touched",
    }
```

## Data Flow

### 1. Data Loading
All data comes from local Parquet/CSV files via `market_store.py`. The store holds 1-minute OHLCV bars per symbol (MNQ, MES, MGC, etc.).

### 2. Timeframe Recomposition (`src/data/recompose.py`)
Higher-timeframe bars (3m, 5m, 7m, 15m, etc.) are recomposed from 1-minute data:
- Bars re-anchor at each **session start** (detected via gaps > 30 minutes in the 1m data)
- Incomplete bars at session start are dropped; partial bars at session end are kept
- This matches TradingView's bar formation behavior

### 3. Warmup Buffer
Indicators need historical data before the backtest start date. The warmup is calculated per-strategy:
```python
STRATEGY_WARMUP_BARS = {
    "EMABreakOsc": 250,   # EMA(30) needs ~120 bars for 99% convergence + MFI cloud ~112
    "DeltaDiv": 200,
    "UTBotSTC": 220,
    ...
}
```
The buffer is converted to calendar days with weekend awareness:
```python
trading_minutes_needed = warmup_bars * minutes_per_bar
trading_days = trading_minutes_needed / (23 * 60)
calendar_days = max(7, int(trading_days * 7 / 5) + 3)
```

### 4. Signal Generation
Each strategy's `generate_signals()` returns a dict with:
- `long_entries`, `short_entries`: boolean Series
- `sl_long`, `sl_short`, `tp1_long`, `tp1_short`: float Series (price levels)
- `ema_main`, `ema_secondary`: Series (for simulator exit logic)
- `debug_frame` (optional): DataFrame with all indicator values for CSV export

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
2. Inherit from `Strategy`
3. Set class attributes and implement `generate_signals()`
4. The strategy is auto-discovered at startup (no registration needed)
5. Add warmup value to `STRATEGY_WARMUP_BARS` in `backend/api.py`

```python
from .base import Strategy
import pandas as pd
import numpy as np

class MyStrategy(Strategy):
    name = "MyStrategy"
    default_params = {"ema_len": 20, "threshold": 0.5}
    param_ranges = {"ema_len": [10, 20, 30], "threshold": [0.3, 0.5, 0.7]}

    # For simulator-based strategies:
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
            "debug_frame": debug_df,        # Optional DataFrame
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
| `src/engine/backtester.py` | Legacy VectorBT wrapper |
| `src/data/recompose.py` | Timeframe recomposition from 1m bars |
| `src/data/market_store.py` | Local market data storage (Parquet/CSV) |
| `src/strategies/base.py` | Abstract Strategy class |
| `src/strategies/ema_break_osc.py` | EMA Break + Oscillator strategy (simulator-based) |
| `src/optimizer/parameter_optimizer.py` | Grid search with session combinations |
| `frontend/src/App.tsx` | React app root, state management |
| `frontend/src/api.ts` | API client, types, defaults |
| `frontend/src/components/Sidebar.tsx` | Backtest configuration UI |
| `frontend/src/components/Dashboard.tsx` | Results display, session filters |

## Contract Specifications

Defined in `FUTURES_SPECS` dict in `backend/api.py`:

| Symbol | Tick Size | Tick Value | Point Value | Fee RT |
|--------|-----------|------------|-------------|--------|
| MNQ    | 0.25      | $0.50      | $2.00       | $0.74  |
| MES    | 0.25      | $1.25      | $5.00       | $0.74  |
| MGC    | 0.10      | $1.00      | $10.00      | $1.24  |
| MBT    | 5.00      | $1.25      | $0.25       | $1.55  |
| NQ     | 0.25      | $5.00      | $20.00      | $2.80  |

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
