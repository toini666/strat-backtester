# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Nebular Apollo** is a quantitative backtesting engine for CME micro-futures strategies. It runs algorithmic strategies translated from TradingView PineScript on local 1-minute OHLCV data, with higher-timeframe recomposition, an event-driven simulator with intra-bar 1m resolution, and a React frontend for visualization, optimization, and market-data management.

**Key technical constraint**: indicator computations must match TradingView PineScript indicators exactly. Strategies are translated from PineScript and the backtester is expected to produce trades identical to TradingView's.

## Quick Start

```bash
# One-shot — installs Homebrew/Python/Node, creates venv, installs deps,
# creates .env from .env.example
bash install.sh

# Daily run — kills port 8001/3001, starts backend + frontend, opens browser
bash start.sh

# Manual run (separate terminals)
source venv/bin/activate
uvicorn backend.main:app --reload --port 8001    # http://localhost:8001
cd frontend && npm run dev -- --port 3001 --host # http://localhost:3001

# Tests
pytest -xvs                                  # all tests
pytest tests/test_simulator.py -xvs          # event-driven simulator
pytest tests/test_api.py -xvs                # API endpoints, sessions
pytest tests/test_recompose.py -xvs          # timeframe recomposition
pytest tests/test_hma_canal.py -xvs          # HMA canal exit logic
pytest tests/test_hma_ssl_osci_v2.py -xvs    # HMA-SSL-Osci v2 strategy
pytest tests/test_data_providers.py -xvs     # data providers / market store
pytest tests/test_simulator.py::test_xxx -xvs  # single test

# Lint frontend
cd frontend && npm run lint
```

Frontend dev server runs on **port 3001** (not Vite's default 5173). `ALLOWED_ORIGINS` defaults to `http://localhost:3001` in `.env.example`; in `ENV=development` (the default), CORS is wide open.

## Architecture

```
Frontend (React/Vite :3001) ──HTTP──▶ Backend (FastAPI :8001)
                                          │
                    ┌─────────────────────┼─────────────────────┐
                    ▼                     ▼                     ▼
            Data Layer             Strategy Engine      Backtest Engine
         market_store.py           strategies/*.py       simulator.py
         recompose.py              base.py (ABC)         (event-driven,
         topstep.py / topstepx.py  indicators.py         intra-bar 1m)
         csv_provider.py           ⟵ pandas_ta_classic
```

Entry points:
- `backend/main.py` — FastAPI app, CORS, mounts `api.router` and `market_data_router`.
- `backend/api.py` — backtest orchestration, strategy registry, optimization, presets (~2200 lines, the largest single file).
- `backend/market_data_routes.py` — CRUD on local market datasets, async download from TopstepX.

## Backtest Engine — Event-Driven Simulator (`src/engine/simulator.py`)

All strategies run through the event-driven simulator (`use_simulator = True` is set on every active strategy). There is **no live VectorBT path** for backtesting; the only remaining VectorBT consumer is the legacy `/optimize` endpoint (it imports `vectorbt` defensively via `try/except`, and the optimization module is flagged as pending refactor).

The simulator processes timeframe bars sequentially. Per bar it:
1. Checks auto-close.
2. Processes intra-bar exits (SL, TP1, breakeven) — zooms into 1m data when a single bar's range spans both SL and TP1 to determine which was hit first.
3. Processes close-based exits (TP2 on EMA cross, fixed-price TP2, SSL baseline cross, HMA canal exits, Supertrend reversal, EMA cross final exit).
4. Processes entries (skipped if blackout, cooldown, or already open).

Building blocks the strategy can opt into:
- **TP1 execution modes**: `"touch"` (immediate) or `"bar_close_if_touched"` (deferred to bar close).
- **Partial exits**: TP1 closes `tp1_partial_pct` of position; TP2 closes `tp2_partial_pct` on EMA cross, fixed price, SSL baseline cross, or HMA inversion. Both default to 0.25.
- **Full TP1**: `tp1_full_exit = True` makes TP1 close the entire position (no breakeven move).
- **Breakeven**: SL moves to entry after TP1 by default; strategies can provide custom `be_long/be_short` series for pre-TP1 breakeven triggers.
- **Supertrend trailing**: optional `supertrend` + `supertrend_trend` series, with `rr_trailing` activation threshold and `sl_buffer` distance.
- **HMA canal exits**: `canal_lower`/`canal_upper`/`canal_green` series + `canal_exit_mode` (`"both_hma"`, `"break_hma"`, `"inversion_hma"`); `inverse_canal_exit` flips long/short logic; `block_loss_canal_exit_before_tp1` suppresses losing exits before TP1.
- **SSL baseline TP2**: `ssl_baseline` series triggers partial exit on close cross with optional `close_partial_min_rr` floor.
- **EMA-cross gating**: `ema_exit_after_tp1_only = True` defers the EMA-cross final exit until TP1 has been hit. `no_sl_after_tp1 = True` disables intra-bar SL/BE after TP1.
- **Custom entry price**: `entry_price_long`/`entry_price_short` override the bar-close entry (used by UTBotAlligatorST for retracement entries).
- **Auto-close**: closes any open position at `auto_close_hour:auto_close_minute` (default **21:00** in reference Brussels time).
- **Blackout windows**: list of active `(start, end)` windows blocking new entries.
- **Cooldown**: minimum bars between trade close and next entry, settable per-strategy or per-signal.
- **Daily win/loss limits**: when enabled, marks subsequent same-day entries as `excluded` (kept in trades list for visibility, excluded from equity).

The exit logic is strategy-agnostic — the simulator drives everything from keys returned by `generate_signals()`.

## Active Strategies

All strategies inherit from `Strategy` (`src/strategies/base.py`), use the simulator, and have a corresponding PineScript file in `Pinescripts/`. They are auto-discovered: every `Strategy` subclass found in `src/strategies/*.py` (excluding `base.py`, `indicators.py`, `__init__.py`) is registered at startup, and `load_strategies()` is re-run on every `/backtest` POST so code changes are picked up without a restart.

| Strategy           | File                          | PineScript                    | Warmup bars |
|--------------------|-------------------------------|-------------------------------|-------------|
| EMABreakOsc        | `ema_break_osc.py`            | `EMA-Break-Osc.txt`           | 250         |
| EMA9Scalp          | `ema9_scalp.py`               | `EMA9-scalp.txt`              | 150         |
| UTBotAlligatorST   | `utbot_alligator_st.py`       | `UTBot-Alligator-ST.txt`      | 120         |
| HMAOsci            | `hma_osci.py`                 | `HMA-Osci.txt`                | 250         |
| HMASSLOsci         | `hma_ssl_osci.py`             | `HMA-SSL-Osci.txt`            | 250         |
| HMASSLOsciV2       | `hma_ssl_osci_v2.py`          | `HMA-SSL-Osci-v2.txt`         | 250         |
| HMASSLOsciV3       | `hma_ssl_osci_v3.py`          | `HMA-SSL-Osci-v3.txt`         | 250         |
| EMABreakHMASSLOsc  | `ema_break_hma_ssl_osc.py`    | `EMA-Break-HMA-SSL-Osc.txt`   | 250         |
| RobReversal        | `rob_reversal.py`             | `RobReversal.txt`             | 150         |
| GatorHMAEpure      | `gator_hma_epure.py`          | `Gator-HMA-Epure.txt`         | DEFAULT (200) |

Warmup defaults to `DEFAULT_WARMUP_BARS = 200` if a strategy is not listed in `STRATEGY_WARMUP_BARS` (in `backend/api.py`). `GatorHMAEpure` currently uses the default — add an explicit entry if you tune its periods.

Strategy class attributes (`src/strategies/base.py`):
- `use_simulator: bool` — must be `True` for the simulator path.
- `manual_exit: bool` — legacy VectorBT flag; harmless on the simulator path.
- `blackout_sensitive: bool` — when `True`, the strategy reads `is_blackout` from the annotated dataframe and adapts its state machine (used by `GatorHMAEpure`).
- `simulator_settings: dict` — class-level defaults; `get_simulator_settings(params)` can override per-call.

## Data Flow

### 1. Data Loading
1-minute OHLCV CSVs live in `data/market_data/<SYMBOL>/<SYMBOL>_<TF>.csv`. `MarketDataStore` (`src/data/market_store.py`) reads them, regenerates higher-timeframe files via `recompose_bars()`, and maintains `data/market_data/index.json` with per-dataset metadata and `contract_segments`.

Active symbols and current front-month contracts (`SYMBOL_CONTRACTS` in `market_store.py`):
- MNQ, MES, MYM, MGC, M2K → `*.M26`
- MBT → `*.K26`
- MCL → `CON.F.US.MCLE.M26`

Data providers in `src/data/`:
- `topstep.py` / `topstepx.py` — Topstep / TopstepX API client (live updates).
- `csv_provider.py` — read-only CSV provider.
- `yfinance_provider.py` — Yahoo Finance fallback (used by the optimizer).
- `base.py` — provider ABC.
- `recompose.py` — 1m → 2m/3m/5m/7m/10m/15m recomposition.

### 2. Timeframe Recomposition (`src/data/recompose.py`)
- Session detection: gaps > 30 minutes in 1m data start a new session.
- Each session is resampled independently with `origin=segment.index[0]`, so bars **re-anchor** at the session open — matches TradingView's bar formation.
- Incomplete leading bars are dropped. The final bar of a session is kept even if partial **iff** another session follows or the bar ends at the daily close (hour 21 or 22 Brussels).
- Supported timeframes: 1m, 2m, 3m, 5m, 7m, 10m, 15m, 30m, 1h, 4h, 1d (only the first seven are recomposed eagerly into CSV; others on demand).

### 3. Warmup Buffer
Indicators need history before the backtest start. Per-strategy warmup is converted to calendar days with weekend awareness:
```python
trading_minutes_needed = STRATEGY_WARMUP_BARS[strategy] * minutes_per_bar
trading_days = trading_minutes_needed / (23 * 60)
calendar_days = max(2, int(trading_days * 7 / 5) + 3)
start_date = original_start_date - timedelta(days=calendar_days)
```
The warmup slice is loaded and used for indicator computation, then discarded before simulation. Debug exports only contain the requested backtest range.

### 4. Signal Generation
`generate_signals(data, params)` returns a dict.

**Required keys:**
- `long_entries`, `short_entries` — bool Series
- `sl_long`, `sl_short`, `tp1_long`, `tp1_short` — float Series (price levels)
- `ema_main`, `ema_secondary` — Series (final-exit and TP2 EMA-cross logic)

**Optional keys** (simulator reads via `signals.get(...)`):
- `cooldown_bars: int` — per-signal cooldown override
- `debug_frame: DataFrame` — full indicator dump for CSV export
- `disable_price_tp1: bool` — skip price-based TP1 entirely (use only close-based partials)
- `be_long`, `be_short` — pre-TP1 breakeven trigger price levels
- `entry_price_long`, `entry_price_short` — override bar-close entry price
- `tp2_long`, `tp2_short` — fixed TP2 price levels (instead of EMA-cross TP2)
- `size_risk_long`, `size_risk_short` — alt price used for position sizing (e.g. size by TP distance for inverse strategies)
- `partial_close_long`, `partial_close_short` — bool Series for close-based partial exits (HyperWave inverse cross etc.)
- `canal_lower`, `canal_upper`, `canal_green` — HMA canal series for canal-based exits
- `canal_exit_requires_arming: bool` — exit only after price first reaches profit side of canal
- `hma_flip_up`, `hma_flip_down` — HMA flip events for inversion-mode canal exits
- `ssl_baseline` — SSL baseline for TP2 cross trigger
- `supertrend`, `supertrend_trend` — Supertrend trailing SL
- `rr_trailing: float` — R:R threshold to activate trailing
- `sl_buffer: float` — buffer for Supertrend trailing SL

### 5. Simulation Output
`simulate()` returns `{metrics, trades, equity_curve, daily_limits_hit}`. Trades list intent: each trade has `legs` (one per partial exit + the final close), an `excluded` flag (true when blocked by a daily limit but still recorded for analytics), and `source` (`"1"`/`"2"` in multi-backtest mode).

## DST-Aware Sessions and Time Handling

CME futures follow US/Eastern. Brussels and ET are normally 6h apart, but DST transition windows (~3 weeks in March, ~1 week in Oct/Nov) drop the offset to 5h, shifting all market times by -1h in Brussels.

**All configured times** (session boundaries, blackout windows, auto-close) are in **reference Brussels time** — the wall-clock time when Brussels–ET = 6h. `_get_market_hour_offset(ts)` computes the DST-driven offset (`0` or `-1`) and `_to_ref_minutes(ts)` shifts the wall-clock back into the reference frame before any comparison.

Consequences:
- No manual config change is needed when backtesting across a DST transition.
- Session labels, blackout windows, and auto-close shift automatically.

### Session Boundaries (reference Brussels time)
| Session | Reference hours |
|---------|-----------------|
| Asia    | 00:00 – 08:59   |
| UK      | 09:00 – 15:29   |
| US      | 15:30 – end     |

There is no "Outside" session — every bar maps to Asia/UK/US. Periods to exclude are configured via blackout windows.

### Default Blackout Windows (`BacktestEngineSettings`)
Active by default: **11:00–13:00**, **15:30–21:00**, **21:00–23:00**. Other windows defined but inactive: 08:00–08:05, 14:30–14:35, 23:00–23:05. Per-strategy overrides exist in the frontend (`STRATEGY_ENGINE_OVERRIDES` in `frontend/src/App.tsx`) — e.g. `HMASSLOsciV2` ships with a different active window.

Default auto-close: **21:00** reference Brussels time. Default daily limits are off; when enabled the defaults are +$500 win / -$700 loss.

## Strategy Implementation Guide

### Adding a New Strategy

1. Create `src/strategies/my_strategy.py` inheriting from `Strategy`.
2. Set `use_simulator = True`, class attributes (`name`, `default_params`, `param_ranges`, `simulator_settings`).
3. Implement `generate_signals()` returning the dict above.
4. Optionally override `get_simulator_settings(params)` for params that toggle simulator behavior.
5. Add the warmup count to `STRATEGY_WARMUP_BARS` in `backend/api.py`.
6. Drop the reference PineScript file into `Pinescripts/`.

The strategy is auto-registered on the next request (or at startup).

```python
from .base import Strategy
import pandas as pd
import pandas_ta_classic as ta

class MyStrategy(Strategy):
    name = "MyStrategy"
    use_simulator = True
    simulator_settings = {"tp1_execution_mode": "bar_close_if_touched"}
    default_params = {"ema_len": 20, "tick_size": 0.25}  # tick_size is injected
    param_ranges = {"ema_len": [10, 20, 30]}

    def generate_signals(self, data, params=None):
        p = self.get_params(params)
        # ... compute indicators / signals ...
        return {
            "long_entries": long_entries, "short_entries": short_entries,
            "sl_long": sl_long, "sl_short": sl_short,
            "tp1_long": tp1_long, "tp1_short": tp1_short,
            "ema_main": ema_main, "ema_secondary": ema_secondary,
            "debug_frame": debug_df,  # optional
        }

    def get_simulator_settings(self, params=None):
        p = self.get_params(params)
        s = self.simulator_settings.copy()
        s["tp1_partial_pct"] = p.get("tp1_partial_pct", 0.25)
        return s
```

### Matching PineScript Indicators

- **EMA**: `pd.Series.ewm(span=n, adjust=False).mean()` — matches Pine's recursive `ta.ema()`.
- **SMA**: `pd.Series.rolling(n).mean()`.
- **HMA / LinReg / others**: use `pandas_ta_classic` (imported as `ta`). The package lives in `libs/pandas-ta/` (folder name kept, but the installed dist is `pandas-ta-classic`). Do **not** install `pandas-ta` from PyPI — formulas diverge.
- **MFI (custom)**: Pine uses `hl2` as source, centered at 0 — see existing strategies for the implementation.
- **Convergence**: EMA(n) reaches ~99% accuracy after ~4n bars after its first valid value. Size warmup for the longest chain (e.g. HMA(84) recomposed from EMAs requires ≥250 bars at 7m).
- **Session boundaries**: gaps between sessions reset resampling anchors — handled by `recompose.py`. Do not depend on continuous bars across the daily break.

## Position Sizing (`src/engine/simulator.py::_calc_size`)

```
risk_amount = initial_equity × risk_per_trade
risk_ticks  = |entry - sl| / tick_size
raw         = risk_amount / (risk_ticks × tick_value)
contracts   = min(max_contracts, max(1.0, int(raw)))
```

Position sizing always returns at least 1 contract (it does not "skip" a trade when the risk distance is too large — that's an intentional behavior for the analytics, but be aware of it when reading equity curves on wide SLs).

Partial exits use the **initial** contract count:
- TP1: `floor(initial × tp1_partial_pct)` contracts
- TP2: `floor(initial × tp2_partial_pct)` contracts
- Remainder closes at the final exit (EMA cross, auto-close, end-of-data).

Example: 9 contracts with 25%/25% → 2 at TP1, 2 at TP2, 5 at final close.

## Multi-Backtest (`POST /backtest/multi`)

Runs **two** configs in parallel on a shared account:
- `mode = "multi_asset"`: two different symbols/strategies; both can hold simultaneously.
- `mode = "multi_strat"`: same symbol, two strategies; a "shared position lock" allows only one open at a time across both streams (the second is dropped). Requires both configs' `symbol` to match.

After running both legs, `_apply_combined_daily_limits()` resets per-asset exclusions and re-runs the daily win/loss limit logic on the merged stream — so the limit reflects the shared account, not each leg in isolation.

## Backtest API

| Endpoint | Purpose |
|----------|---------|
| `GET  /strategies` | Registered strategies + `default_params`. |
| `GET  /strategy-param-ranges/{name}` | `param_ranges` for the optimizer. |
| `GET  /available-data` | Symbols, timeframes, date ranges, per-strategy min start datetime. |
| `POST /backtest` | Full single-config backtest. Re-runs `load_strategies()` each call. |
| `POST /backtest/resimulate` | Fast path that reuses cached signals (only re-runs the simulator with new risk/engine params). |
| `POST /backtest/multi` | Two-config multi-asset / multi-strat backtest. |
| `POST /optimize` | Legacy grid search (uses VectorBT via `try/except`; pending refactor). |
| `GET  /optimization-history` | List past runs from `~/.nebular-apollo/optimization_history.json`. |
| `GET  /optimization-history/{id}` | Full run details. |
| `DELETE /optimization-history/{id}` | Remove one run. |
| `POST /optimization-history/bulk-delete` | Remove many. |
| `POST /optimization-history/{id}/favorite` | Toggle favorite flag. |
| `GET/POST/DELETE/PUT /presets` | CRUD on saved backtest configurations (`data/presets.json`). |
| `GET  /market-data` | Local datasets metadata. |
| `POST /market-data/download` | Async download from TopstepX. |
| `GET  /market-data/download/{id}/status` | Poll download progress. |
| `DELETE /market-data/{dataset_id}` | Drop a dataset. |

The `/backtest` flow populates `SIGNAL_CACHE` so that subsequent `/backtest/resimulate` calls (triggered by UI sliders for risk/engine params) skip signal generation entirely.

## Contract Switches (Rollovers)

When a futures contract expires:

1. **Write a one-time script** following the templates in `scripts/contract_switch_*.py`:
   - Fetch remaining bars for the **old contract** up to the day before the rollover and `save_bars(symbol, OLD_CONTRACT_ID, data)` — same contract, appended.
   - Fetch bars for the **new contract** starting at the first bar of the new CME session and `save_bars(symbol, NEW_CONTRACT_ID, data)` — `save_bars` detects the contract change, appends only post-`existing_end` rows, and adds a new entry to `contract_segments`.
2. **Update `SYMBOL_CONTRACTS`** in `src/data/market_store.py` to the new contract ID.
3. Existing scripts in `scripts/`: `contract_switch_MBT_J26.py`, `contract_switch_MBT_K26.py`, `contract_switch_MGC_M26.py`, `fix_contract_switch_MBT_J26.py`, `import_mcl_databento_2025.py`, `update_market_data.py`.

**CME month codes**: F=Jan, G=Feb, H=Mar, J=Apr, K=May, M=Jun, N=Jul, Q=Aug, U=Sep, V=Oct, X=Nov, Z=Dec.

**Time reference for switch dates**: Brussels is CET (UTC+1) from late October to late March, CEST (UTC+2) otherwise. CME opens at 17:00 ET — which is 22:00 UTC in summer / 23:00 UTC in winter (Brussels local time both ~22:00–23:00). The gap between the last bar of the old contract and the first of the new contract is the inter-session gap.

**CSV format**: `Date,Open,High,Low,Close,Volume` with Brussels tz-aware timestamps. Mixed offsets within a file are fine — `market_store.py` reads via `pd.to_datetime(utc=True)` then `tz_convert("Europe/Brussels")`.

## Contract Specifications

`CONTRACT_SPECS` and `FEES_MAP` are in `backend/api.py` (lines ~309 and ~328). Active micro-futures:

| Symbol | Tick Size | Tick Value | Point Value | Fee RT |
|--------|-----------|------------|-------------|--------|
| M2K    | 0.10      | $0.50      | $5.00       | $0.74  |
| MBT    | 5.00      | $0.50      | $0.10       | $2.34  |
| MCL    | 0.01      | $1.00      | $100.00     | $1.04  |
| MES    | 0.25      | $1.25      | $5.00       | $0.74  |
| MGC    | 0.10      | $1.00      | $10.00      | $1.24  |
| MNQ    | 0.25      | $0.50      | $2.00       | $0.74  |
| MYM    | 1.00      | $0.50      | $0.50       | $0.74  |

`Fee RT` shown here is the exchange + clearing round-turn fee from `FEES_MAP`. The simulator applies an additional **`COMMISSION_PER_CONTRACT_RT = $0.50`** (Topstep broker commission) on top — added inside `_contract_backtest_specs()` and the optimizer's Topstep contract path. Effective round-turn cost = `FEES_MAP[symbol] + 0.50`.

Full-size ES/NQ/RTY/YM/GC/CL/SI/HG/6A/6E/6B specs are also present for FEES_MAP/CONTRACT_SPECS lookups, even though no historical data is loaded for them.

## Goal-Driven Backtest Campaigns

Optimization campaigns triggered via `/goal` (see `prompt-goal-backtests.md`) follow a strict structure to keep the repo navigable when many campaigns accumulate.

### Directory layout

```
scripts/
├─ contract_switch_*.py                          # operational tools (kept at top level)
├─ update_market_data.py
└─ goals/
   ├─ _shared/                                   # reusable across campaigns
   │  ├─ harness.py            run_backtest, summarize, fmt_summary, bench
   │  ├─ engine_settings.py    ui_default_engine_settings, make_engine_settings
   │  ├─ preset.py             build_preset, write_preset, replay_preset, verify_preset
   │  └─ analysis.py           bucket_by_hour, bucket_by_dow, print tables
   └─ <YYYY-MM-DD>_<Strategy>_<Symbol>/          # ONE folder per campaign
      ├─ README.md
      ├─ sweeps/
      │  ├─ _campaign.py       campaign-local constants
      │  ├─ 01_baseline_tfs.py … 08_final_validation.py
      ├─ logs/                 one .log per sweep
      ├─ winner_preset.json
      ├─ verify_preset.py      must print ✅ MATCH
      └─ REPORT.md
```

Reference example: `scripts/goals/2026-05-15_HMASSLOsciV3_MNQ/`.

### Critical rules for `/goal` agents

1. **Campaign files NEVER at top level of `scripts/`** — only operational tools (`contract_switch_*`, `update_market_data`) live there.
2. **Always go through `_shared/harness.py::run_backtest`** for any backtest call. It auto-applies the UI's per-strategy defaults via `ui_default_engine_settings()` — never construct `BacktestEngineSettings()` manually, you'll get the wrong defaults and produce results that don't reproduce in the UI.
3. **`_shared/engine_settings.py` is a Python mirror of the frontend defaults** (`DEFAULT_BACKTEST_ENGINE_SETTINGS` in `frontend/src/api.ts` + `STRATEGY_ENGINE_OVERRIDES` in `frontend/src/App.tsx`). When the frontend defaults change, update this mirror in lockstep.
4. **`auto_close_hour` is fixed at 22 (CME close, reference Brussels time)** for every winning preset. It can be touched diagnostically but the final config MUST have `auto_close_hour = 22`.
5. **Daily limits default order**: try `intra_bar` mode first, fall back to `after_close` only if intra-bar breaks the edge.
6. **Preset is the deliverable contract**: every campaign produces a `winner_preset.json` in the UI format (riskPerTrade as percent, all blackouts explicit, all `default_params` included). `write_preset` inserts it into `data/presets.json` automatically so it shows up in the UI favorites.
7. **`verify_preset.py` is mandatory** — replays the preset and compares to expected metrics. If it doesn't print `✅ MATCH`, the campaign is not done.
8. **Sweep filenames are neutral** — `03_strategy_params.py`, not `03_osc_core_params.py`. Strategy-specific jargon (`osc`, `hma`, etc.) belongs in the content, not the filename.

### Frontend vs backend default discrepancy (important gotcha)

The Python `BacktestEngineSettings` class in `backend/api.py` has DIFFERENT defaults from what the UI sends:

| | Backend `BacktestEngineSettings` | Frontend (UI defaults) |
|-|-|-|
| `auto_close_hour` | 21 | 22 |
| Active blackouts (raw) | 11-13, 15:30-21, 21-23 | 12-14, 16:30-22, 22-23:59 |
| Per-strategy overrides | none | `HMASSLOsciV2/V3` → only 22-23:59 |

**The UI defaults are the source of truth for goal campaigns.** A backtest run with backend defaults will not reproduce in the UI. `_shared/harness.py` enforces this automatically by calling `ui_default_engine_settings(strategy_name)`.

## Important Conventions

1. **All times in Brussels timezone** — data is stored/indexed in UTC, business logic operates in `Europe/Brussels`.
2. **Reference frame for configured times** — blackout, auto-close, session boundaries use reference Brussels time (offset 0). DST misalignment shifts ref→wall-clock automatically.
3. **No "Outside" session** — every bar is Asia, UK, or US.
4. **Warmup ≠ backtest data** — warmup bars are loaded before the requested start, used only to converge indicators, and dropped before simulation and debug export.
5. **Strategy auto-discovery** — any `Strategy` subclass under `src/strategies/` is registered automatically; `load_strategies()` is re-run on every `/backtest` request, so code edits are picked up without server restart.
6. **`pandas-ta-classic`, not `pandas-ta`** — the installed package is `pandas-ta-classic` (path `libs/pandas-ta/`, import name `pandas_ta_classic`). The PyPI `pandas-ta` package has divergent formulas. The `Indicators` helper is a no-op stub kept for backwards compatibility.
7. **Single backtest engine** — all strategies use the event-driven simulator. The legacy VectorBT path is gone for `/backtest`; only `/optimize` still tries to import `vectorbt` (defensively, via `try/except`).
8. **`tick_size` is injected** — `_run_simulator_backtest` writes the active symbol's `tick_size` into `params` before calling `generate_signals`, so strategies that round to ticks can read `params["tick_size"]` directly.
9. **UI defaults are the source of truth for engine settings** — the Python `BacktestEngineSettings` class has *different* defaults from the frontend. The UI overrides them when sending requests, and goal campaigns must match the UI to be reproducible. Use `scripts/goals/_shared/engine_settings.ui_default_engine_settings(strategy_name)` rather than `BacktestEngineSettings()` directly.
10. **Auto-close is 22:00 reference Brussels for any final config** — that's the CME daily close in winter-equivalent reference time. Diagnostic sweeps may touch it, but no winning preset / saved favorite should have any other value.

## Key Files

| File | Purpose |
|------|---------|
| `backend/main.py` | FastAPI app, CORS, logging, rate limiter mount. |
| `backend/api.py` | Backtest orchestration, strategy registry, optimization, presets, signal cache. |
| `backend/market_data_routes.py` | Market data CRUD + async download. |
| `src/engine/simulator.py` | Event-driven simulator with intra-bar 1m resolution and all exit modes. |
| `src/data/market_store.py` | Local CSV storage, index, `SYMBOL_CONTRACTS`, contract-segment tracking. |
| `src/data/recompose.py` | Per-session 1m → higher-TF recomposition. |
| `src/data/topstep.py` / `topstepx.py` | Topstep / TopstepX API clients. |
| `src/strategies/base.py` | `Strategy` ABC. |
| `src/strategies/*.py` | One file per strategy (see table above). |
| `src/optimizer/parameter_optimizer.py` | Grid-search optimizer (legacy VectorBT, pending refactor). |
| `src/optimizer/grid_search.py` | Helper for grid-search combinations. |
| `frontend/src/App.tsx` | React root, app modes (backtest / optimization / data / favorites), strategy-specific engine overrides. |
| `frontend/src/api.ts` | API client, TypeScript types, defaults. |
| `frontend/src/components/Sidebar.tsx` | Backtest configuration UI. |
| `frontend/src/components/Dashboard.tsx` | Results, KPIs, equity curve, trades. |
| `frontend/src/components/MarketDataPanel.tsx` | Local dataset management UI. |
| `frontend/src/components/OptimizationConfig.tsx` / `OptimizationResults.tsx` / `OptimizationHistory.tsx` | Optimizer screens. |
| `frontend/src/components/FavoritesPage.tsx` | Saved presets / favorited optimization runs. |
| `pytest.ini` | pytest config (`testpaths=tests`). |
| `requirements.txt` | Python deps; installs `-e ./libs/pandas-ta` (= the `pandas-ta-classic` package). |
| `prompt-goal-backtests.md` | Template prompt for `/goal` backtest campaigns. Fill the variables block, paste, fire. |
| `scripts/goals/_shared/harness.py` | Reusable backtest harness (cached bars, UI-default engine settings, bench helper). |
| `scripts/goals/_shared/engine_settings.py` | Python mirror of frontend UI defaults + per-strategy overrides. |
| `scripts/goals/_shared/preset.py` | Build / write / replay / verify presets in the UI format. |
| `scripts/goals/_shared/analysis.py` | Hour-of-day and day-of-week trade bucketing for blackout discovery. |
| `scripts/goals/<slug>/` | One folder per campaign — sweeps, logs, preset, verify, report. |
| `data/presets.json` | UI favorites storage. `write_preset` inserts campaign winners here. |
