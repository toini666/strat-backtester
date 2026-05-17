"""HMASSLOsciV3 — analyse instrumentée des 3 presets gagnants.

Pour chaque trade actif des 3 winners (MNQ v4 single, MGC v2 single,
MNQ+MGC multi-asset), reconstruit :
  - état des indicateurs à l'entrée et à la sortie (hw, sgd, mfi, canal…)
  - MAE / MFE / R-multiple
  - temps jusqu'au prochain HW cross après entrée et après sortie
  - "shadow" : et si on attendait UN HW de plus avant de sortir ?
  - pente du canal (∆canal_lower & ∆canal_upper) sur N bars avant entrée
  - largeur du canal à l'entrée
  - flip du canal pendant la vie du trade

Aucune modification de stratégie. Lecture seule, sorties CSV/MD dans
``outputs/``.
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

OUT = Path(__file__).resolve().parent / "outputs"
OUT.mkdir(parents=True, exist_ok=True)

from backend.api import (  # noqa: E402
    BacktestEngineSettings,
    DEFAULT_WARMUP_BARS,
    STRATEGIES,
    STRATEGY_WARMUP_BARS,
    _annotate_blackout_flags,
    _build_blackout_windows,
    _contract_backtest_specs,
    _normalize_backtest_datetime,
    _slice_from_start,
    load_strategies,
)
from src.data import market_store as ms_module  # noqa: E402
from src.data.market_store import SYMBOL_CONTRACTS  # noqa: E402
from src.engine.simulator import SimulatorConfig, simulate as simulate_strategy  # noqa: E402


# ---------------------------------------------------------------------------
# Preset loading
# ---------------------------------------------------------------------------

PRESETS = {
    "MNQ_v4": ROOT / "scripts/goals/2026-05-16_HMASSLOsciV3_MNQ_v4/winner_preset.json",
    "MGC_v2": ROOT / "scripts/goals/2026-05-16_HMASSLOsciV3_MGC_v2/winner_preset.json",
    "MNQ_MGC": ROOT / "scripts/goals/2026-05-16_HMASSLOsciV3_MNQ_MGC/winner_preset.json",
}


def _engine_from_dict(d: Dict[str, Any]) -> BacktestEngineSettings:
    """Build a BacktestEngineSettings from the preset's engineSettings dict."""
    return BacktestEngineSettings(
        auto_close_enabled=d.get("auto_close_enabled", True),
        auto_close_hour=int(d.get("auto_close_hour", 22)),
        auto_close_minute=int(d.get("auto_close_minute", 0)),
        blackout_windows=list(d.get("blackout_windows", [])),
        debug=False,
        daily_win_limit_enabled=bool(d.get("daily_win_limit_enabled", False)),
        daily_win_limit=float(d.get("daily_win_limit", 500.0)),
        daily_loss_limit_enabled=bool(d.get("daily_loss_limit_enabled", False)),
        daily_loss_limit=float(d.get("daily_loss_limit", 700.0)),
        daily_limit_mode=str(d.get("daily_limit_mode", "after_close")),
    )


def _flatten(preset: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Yield {symbol, interval, strategy, params, risk, engine, label} per leg."""
    if preset.get("mode") == "multi_asset":
        legs = []
        for i, cfg in enumerate(preset["configs"]):
            legs.append({
                "label": f"{cfg['symbol']}_in_combo",
                "symbol": cfg["symbol"],
                "interval": cfg["interval"],
                "strategy": cfg["strategyName"],
                "params": cfg["params"],
                "risk": float(cfg["riskPerTrade"]) / 100.0,
                "max_contracts": int(cfg.get("maxContracts", 50)),
                "engine": _engine_from_dict(cfg["engineSettings"]),
                "start": preset["startDatetime"],
                "end": preset["endDatetime"],
                "initial_equity": float(preset["initialEquity"]),
            })
        return legs
    # single
    return [{
        "label": "single",
        "symbol": preset["symbol"],
        "interval": preset["interval"],
        "strategy": preset["strategyName"],
        "params": preset["params"],
        "risk": float(preset["riskPerTrade"]) / 100.0,
        "max_contracts": int(preset.get("maxContracts", 50)),
        "engine": _engine_from_dict(preset["engineSettings"]),
        "start": preset["startDatetime"],
        "end": preset["endDatetime"],
        "initial_equity": float(preset["initialEquity"]),
    }]


# ---------------------------------------------------------------------------
# Replay one leg
# ---------------------------------------------------------------------------

_DATA_CACHE: Dict[Tuple, pd.DataFrame] = {}
_DATA_1M_CACHE: Dict[Tuple, pd.DataFrame] = {}


def _load_data(symbol: str, contract_id: str, interval: str,
               original_start: pd.Timestamp, end: pd.Timestamp,
               warmup_bars: int):
    from datetime import timedelta
    map_min = {"1m": 1, "2m": 2, "3m": 3, "5m": 5, "7m": 7, "10m": 10, "15m": 15}
    minutes_per_bar = map_min.get(interval, 15)
    trading_minutes_needed = warmup_bars * minutes_per_bar
    trading_days = trading_minutes_needed / (23 * 60)
    calendar_days = max(2, int(trading_days * 7 / 5) + 3)
    start_date = original_start - timedelta(days=calendar_days)

    key = (symbol, interval, str(start_date), str(end))
    if key not in _DATA_CACHE:
        store = ms_module.MarketDataStore()
        _DATA_CACHE[key] = store.load_bars(contract_id, start_date, end, interval)
    key_1m = (symbol, "1m", str(start_date), str(end))
    if key_1m not in _DATA_1M_CACHE:
        store = ms_module.MarketDataStore()
        _DATA_1M_CACHE[key_1m] = store.load_bars(contract_id, start_date, end, "1m")
    return _DATA_CACHE[key], _DATA_1M_CACHE[key_1m]


@dataclass
class LegRun:
    label: str
    symbol: str
    interval: str
    bars: pd.DataFrame              # sliced (post-warmup) bars
    debug: pd.DataFrame              # debug_frame from strategy.generate_signals
    trades: List[Dict[str, Any]]
    signals: Dict[str, Any]
    specs: Dict[str, float]


def run_leg(leg: Dict[str, Any]) -> LegRun:
    load_strategies()
    strat_cls = STRATEGIES[leg["strategy"]]
    contract_id = SYMBOL_CONTRACTS[leg["symbol"]]
    specs = _contract_backtest_specs(leg["symbol"])

    original_start = _normalize_backtest_datetime(leg["start"])
    end_date = _normalize_backtest_datetime(leg["end"])
    warmup = STRATEGY_WARMUP_BARS.get(leg["strategy"], DEFAULT_WARMUP_BARS)
    data, data_1m = _load_data(leg["symbol"], contract_id, leg["interval"],
                                original_start, end_date, warmup)

    strat = strat_cls()
    params = dict(strat_cls.default_params)
    params.update(leg["params"])
    params["tick_size"] = specs["tick_size"]

    simulator_settings = strat.get_simulator_settings(params)
    blackout_windows = _build_blackout_windows(leg["engine"])
    annotated = _annotate_blackout_flags(data, blackout_windows)
    signals = strat.generate_signals(annotated, params)

    sliced, mask = _slice_from_start(data, original_start)
    sliced_signals = {}
    for k, v in signals.items():
        if isinstance(v, pd.Series):
            sliced_signals[k] = v.loc[mask]
        elif isinstance(v, pd.DataFrame):
            sliced_signals[k] = v.loc[mask]
        else:
            sliced_signals[k] = v
    data_1m_sliced, _ = _slice_from_start(data_1m, original_start)

    eng = leg["engine"]
    cfg = SimulatorConfig(
        initial_equity=leg["initial_equity"],
        risk_per_trade=leg["risk"],
        max_contracts=leg["max_contracts"],
        tick_size=specs["tick_size"],
        tick_value=specs["tick_value"],
        point_value=specs["point_value"],
        fee_per_trade=specs["fee_per_trade"],
        auto_close_enabled=eng.auto_close_enabled,
        auto_close_hour=eng.auto_close_hour,
        auto_close_minute=eng.auto_close_minute,
        blackout_windows=blackout_windows,
        cooldown_bars=int(sliced_signals.get("cooldown_bars",
                                             params.get("cooldown_bars", 0))),
        tp1_execution_mode=str(simulator_settings.get("tp1_execution_mode", "touch")),
        tp1_partial_pct=float(simulator_settings.get("tp1_partial_pct", 0.25)),
        tp2_partial_pct=float(simulator_settings.get("tp2_partial_pct", 0.25)),
        ema_exit_after_tp1_only=bool(simulator_settings.get("ema_exit_after_tp1_only", False)),
        no_sl_after_tp1=bool(simulator_settings.get("no_sl_after_tp1", False)),
        tp1_full_exit=bool(simulator_settings.get("tp1_full_exit", False)),
        inverse_canal_exit=bool(simulator_settings.get("inverse_canal_exit", False)),
        canal_exit_mode=str(simulator_settings.get("canal_exit_mode", "break_hma")),
        block_loss_canal_exit_before_tp1=bool(
            simulator_settings.get("block_loss_canal_exit_before_tp1", False)
        ),
        close_partial_min_rr=float(simulator_settings.get("close_partial_min_rr", 0.0)),
        one_trade_per_setup_window=bool(
            simulator_settings.get("one_trade_per_setup_window", False)
        ),
        final_exit_pct=float(simulator_settings.get("final_exit_pct", 0.0)),
        daily_win_limit_enabled=eng.daily_win_limit_enabled,
        daily_win_limit=eng.daily_win_limit,
        daily_loss_limit_enabled=eng.daily_loss_limit_enabled,
        daily_loss_limit=eng.daily_loss_limit,
        daily_limit_mode=eng.daily_limit_mode,
    )

    result = simulate_strategy(
        data=sliced,
        data_1m=data_1m_sliced,
        signals=sliced_signals,
        config=cfg,
        ema_main=sliced_signals["ema_main"],
        ema_secondary=sliced_signals["ema_secondary"],
    )

    debug_df = sliced_signals.get("debug_frame")
    if debug_df is None:
        raise RuntimeError("Strategy did not return debug_frame")
    return LegRun(
        label=leg["label"],
        symbol=leg["symbol"],
        interval=leg["interval"],
        bars=sliced,
        debug=debug_df,
        trades=result["trades"],
        signals=sliced_signals,
        specs=specs,
    )


# ---------------------------------------------------------------------------
# Per-trade analytics
# ---------------------------------------------------------------------------

def _find_idx(idx: pd.DatetimeIndex, ts: pd.Timestamp) -> Optional[int]:
    pos = idx.get_indexer([ts], method="nearest")[0]
    if pos < 0:
        return None
    return int(pos)


def analyze_leg(run: LegRun) -> pd.DataFrame:
    """Build a trade-level DataFrame with indicator context."""
    bars = run.bars
    dbg = run.debug
    pv = run.specs["point_value"]
    fee_per = run.specs["fee_per_trade"]
    # The strategy's setup_bar_* columns store INTEGER indices into the
    # full (warmup-included) bars array, not the sliced index. Compute the
    # warmup offset once so we can convert to a bars-since-setup value
    # relative to the sliced frame.
    _setup_long_arr = dbg["setup_bar_long"].values
    _setup_short_arr = dbg["setup_bar_short"].values
    _valid_offsets = []
    for _ii in range(len(dbg)):
        for _arr in (_setup_long_arr, _setup_short_arr):
            v = _arr[_ii]
            if v >= 0:
                # offset = stored_index - sliced_index, so a "bars since setup"
                # within the window means stored - sliced ∈ [warmup, warmup+window]
                _valid_offsets.append(int(v) - _ii)
                break
        if len(_valid_offsets) > 1000:
            break
    _warmup_offset = max(_valid_offsets) if _valid_offsets else 0

    high = bars["High"].values
    low = bars["Low"].values
    close_ = bars["Close"].values
    hw_over = dbg["hw_cross_over"].values.astype(bool)
    hw_under = dbg["hw_cross_under"].values.astype(bool)
    canal_lower = dbg["canal_lower"].values
    canal_upper = dbg["canal_upper"].values
    canal_green = dbg["canal_green"].values
    hma1 = dbg["hma1"].values
    hma2 = dbg["hma2"].values
    bbmc = dbg["bbmc_ssl"].values
    osc_sig = dbg["osc_sig"].values
    osc_sgd = dbg["osc_sgd"].values
    mfi = dbg["mfi"].values
    setup_bar_long = dbg["setup_bar_long"].values
    setup_bar_short = dbg["setup_bar_short"].values

    n = len(bars)
    idx = bars.index

    rows: List[Dict[str, Any]] = []
    for t in run.trades:
        if t.get("excluded"):
            continue
        side = 1 if t["side"] == "Long" else -1
        entry_ts = pd.Timestamp(t["entry_time"])
        exit_ts = pd.Timestamp(t["exit_time"])
        ei = _find_idx(idx, entry_ts)
        xi = _find_idx(idx, exit_ts)
        if ei is None or xi is None:
            continue

        entry_px = float(t["entry_price"])
        sl_at_entry = t.get("legs", [{}])[-1].get("entry_price")  # not stored; we re-extract
        # SL/RR via first leg actually executed: use the partial_exits first or fallback to compute
        sl_px = None
        # legs[-1] is the final close; the SL price isn't stored explicitly on the trade
        # but: t['legs'][-1]['exit_price'] = effective close, and t['status'] tells the reason
        status = t["status"]

        # MFE / MAE across the trade life on close-bar OHLC
        if xi >= ei and ei < n:
            window_hi = high[ei:xi + 1]
            window_lo = low[ei:xi + 1]
            window_cl = close_[ei:xi + 1]
            if side == 1:
                mfe_px = float(np.max(window_hi)) - entry_px
                mae_px = entry_px - float(np.min(window_lo))
            else:
                mfe_px = entry_px - float(np.min(window_lo))
                mae_px = float(np.max(window_hi)) - entry_px
        else:
            mfe_px = mae_px = np.nan

        # SL distance from initial: derive from sizing + pnl
        # The trade's pnl + fees / size_contracts = points moved.
        # We can recover initial SL via simulator size formula:
        # initial_risk_$ = initial_equity * risk_per_trade ≈ size * |entry-sl| * tick_value/tick_size
        # but we'd need leg info. Cheaper: use the strategy's debug "sl_long/short" series.
        if side == 1:
            sl_series = dbg.get("sl_long")
        else:
            sl_series = dbg.get("sl_short")
        sl_arr = sl_series.values if sl_series is not None else None
        sl_at_entry = float(sl_arr[ei]) if sl_arr is not None and not np.isnan(sl_arr[ei]) else np.nan
        sl_dist_px = abs(entry_px - sl_at_entry) if not np.isnan(sl_at_entry) else np.nan
        r_realized = (
            ((window_cl[-1] - entry_px) * side) / sl_dist_px
            if sl_dist_px and sl_dist_px > 0 and not np.isnan(window_cl[-1])
            else np.nan
        )

        # R-multiple at exit (using actual exit price, not last close)
        exit_px_actual = float(t["exit_price"])
        r_exit = ((exit_px_actual - entry_px) * side) / sl_dist_px if sl_dist_px and sl_dist_px > 0 else np.nan

        # MFE in R units
        mfe_r = mfe_px / sl_dist_px if sl_dist_px and sl_dist_px > 0 else np.nan
        mae_r = mae_px / sl_dist_px if sl_dist_px and sl_dist_px > 0 else np.nan

        # Indicator state at entry
        e_canal_low = float(canal_lower[ei]) if not np.isnan(canal_lower[ei]) else np.nan
        e_canal_up = float(canal_upper[ei]) if not np.isnan(canal_upper[ei]) else np.nan
        canal_width_e = (e_canal_up - e_canal_low) if not (np.isnan(e_canal_up) or np.isnan(e_canal_low)) else np.nan
        canal_green_e = bool(canal_green[ei])

        # Canal slope: (canal_lower[ei] - canal_lower[ei-5]) / 5 bars
        L = 5
        if ei >= L and not np.isnan(canal_lower[ei - L]) and not np.isnan(canal_lower[ei]):
            slope_low = (canal_lower[ei] - canal_lower[ei - L]) / L
            slope_up = (canal_upper[ei] - canal_upper[ei - L]) / L
            slope_mid = (slope_low + slope_up) / 2.0
        else:
            slope_low = slope_up = slope_mid = np.nan
        # Normalize slope as pct of price (per bar)
        slope_pct_per_bar = (slope_mid / entry_px * 100.0) if entry_px and not np.isnan(slope_mid) else np.nan

        # HMA1 vs HMA2 spread (relative to canal width)
        hma_spread = float(hma1[ei] - hma2[ei]) if not np.isnan(hma1[ei]) and not np.isnan(hma2[ei]) else np.nan
        hma_spread_pct = (hma_spread / entry_px * 100.0) if entry_px else np.nan
        # SSL (bbmc) vs HMA1 distance — measures setup recency
        bbmc_dist = float(bbmc[ei] - hma2[ei]) if not (np.isnan(bbmc[ei]) or np.isnan(hma2[ei])) else np.nan

        # Hyperwave amplitude at entry
        hw_at_entry = float(osc_sig[ei]) if not np.isnan(osc_sig[ei]) else np.nan
        sgd_at_entry = float(osc_sgd[ei]) if not np.isnan(osc_sgd[ei]) else np.nan
        mfi_at_entry = float(mfi[ei]) if not np.isnan(mfi[ei]) else np.nan
        # Distance hw->sgd at entry (momentum spread)
        hw_sgd_spread_e = (hw_at_entry - sgd_at_entry) if not (np.isnan(hw_at_entry) or np.isnan(sgd_at_entry)) else np.nan

        # Hyperwave at exit
        hw_at_exit = float(osc_sig[xi]) if not np.isnan(osc_sig[xi]) else np.nan
        canal_green_x = bool(canal_green[xi])
        canal_flipped = canal_green_e != canal_green_x

        # Bars from setup_bar to entry (entry window position).
        # setup_bar_* values are indices in the full (warmup-included) array;
        # subtract _warmup_offset to project into the sliced frame.
        if side == 1:
            sb_raw = int(setup_bar_long[ei]) if setup_bar_long[ei] >= 0 else -1
        else:
            sb_raw = int(setup_bar_short[ei]) if setup_bar_short[ei] >= 0 else -1
        if sb_raw >= 0:
            setup_bar_sliced = sb_raw - _warmup_offset
            bars_since_setup = ei - setup_bar_sliced
        else:
            bars_since_setup = -1

        # First HW cross AFTER entry (opposite-direction = real "exit HW")
        # We look for first index after ei where hw_over (for long pos this is bullish HW = does NOT exit)
        # vs hw_under (bearish HW = exit). For symmetry: first cross of either direction.
        first_hw_after_entry = None
        first_hw_dir = None
        for j in range(ei + 1, min(n, ei + 200)):
            if hw_over[j] or hw_under[j]:
                first_hw_after_entry = j - ei
                first_hw_dir = 1 if hw_over[j] else -1
                break

        # First HW AFTER the exit (used for "should we have waited?" question)
        first_hw_after_exit = None
        first_hw_after_exit_dir = None
        first_hw_after_exit_close = None
        for j in range(xi + 1, min(n, xi + 200)):
            if hw_over[j] or hw_under[j]:
                first_hw_after_exit = j - xi
                first_hw_after_exit_dir = 1 if hw_over[j] else -1
                first_hw_after_exit_close = float(close_[j])
                break

        # Shadow exit if we had waited 1 more HW
        if first_hw_after_exit_close is not None:
            shadow_exit_r = ((first_hw_after_exit_close - entry_px) * side) / sl_dist_px if sl_dist_px and sl_dist_px > 0 else np.nan
        else:
            shadow_exit_r = np.nan

        rows.append({
            "leg": run.label,
            "symbol": run.symbol,
            "entry_time": str(entry_ts),
            "exit_time": str(exit_ts),
            "side": t["side"],
            "session": t.get("session"),
            "hour": entry_ts.hour,
            "dow": entry_ts.dayofweek,
            "status": status,
            "pnl": t["pnl"],
            "size": t["size"],
            "bars_in_trade": xi - ei,
            "entry_px": entry_px,
            "exit_px": exit_px_actual,
            "sl_px": sl_at_entry,
            "sl_dist_pts": sl_dist_px,
            "sl_dist_pct": (sl_dist_px / entry_px * 100.0) if entry_px and not np.isnan(sl_dist_px) else np.nan,
            "r_at_exit": r_exit,
            "mfe_pts": mfe_px,
            "mae_pts": mae_px,
            "mfe_r": mfe_r,
            "mae_r": mae_r,
            "canal_width_e": canal_width_e,
            "canal_width_pct_e": (canal_width_e / entry_px * 100.0) if entry_px and not np.isnan(canal_width_e) else np.nan,
            "canal_slope_pct_per_bar": slope_pct_per_bar,
            "canal_green_e": canal_green_e,
            "canal_green_x": canal_green_x,
            "canal_flipped": canal_flipped,
            "hma_spread_pct": hma_spread_pct,
            "bbmc_minus_hma2": bbmc_dist,
            "hw_at_entry": hw_at_entry,
            "sgd_at_entry": sgd_at_entry,
            "mfi_at_entry": mfi_at_entry,
            "hw_sgd_spread_e": hw_sgd_spread_e,
            "hw_at_exit": hw_at_exit,
            "bars_since_setup": bars_since_setup,
            "first_hw_after_entry_bars": first_hw_after_entry,
            "first_hw_after_entry_dir": first_hw_dir,
            "first_hw_after_exit_bars": first_hw_after_exit,
            "first_hw_after_exit_dir": first_hw_after_exit_dir,
            "first_hw_after_exit_close": first_hw_after_exit_close,
            "shadow_exit_r": shadow_exit_r,
        })

    df = pd.DataFrame(rows)
    return df


# ---------------------------------------------------------------------------
# Aggregate reports
# ---------------------------------------------------------------------------

def summary_by_status(df: pd.DataFrame) -> pd.DataFrame:
    g = df.groupby("status", dropna=False).agg(
        n=("pnl", "count"),
        pnl=("pnl", "sum"),
        avg_pnl=("pnl", "mean"),
        win_rate=("pnl", lambda s: float((s > 0).mean()) * 100.0),
        avg_bars=("bars_in_trade", "mean"),
        avg_r=("r_at_exit", "mean"),
        med_r=("r_at_exit", "median"),
        avg_mfe_r=("mfe_r", "mean"),
        avg_mae_r=("mae_r", "mean"),
    ).round(2).reset_index().sort_values("pnl", ascending=False)
    return g


def hw_wait_one_more(df: pd.DataFrame) -> Dict[str, Any]:
    """For Canal Exit trades, simulate "wait one more HW" and compare R AND $.

    Decides whether the "wait one more HW" rule is an actual strategy
    improvement or only selection bias on losers — by reporting net $/trade
    delta across ALL Canal Exits, not just the subset of losers.
    """
    canal = df[df["status"] == "Canal Exit"].copy()
    if canal.empty:
        return {}
    actual = canal["r_at_exit"]
    shadow = canal["shadow_exit_r"]
    # split by actual outcome
    losers = canal[canal["r_at_exit"] < 0]
    winners = canal[canal["r_at_exit"] >= 0]

    # Dollar delta: ∆R * (size * sl_dist_pts * point_value).
    # We don't carry point_value at this point; approximate via pnl / r_at_exit
    # but ONLY when |r_at_exit| ≥ 0.05 to avoid division blow-ups. For the
    # remainder fall back to the median per_R_$ of the filtered set.
    canal = canal.copy()
    canal["per_R_$"] = np.where(
        canal["r_at_exit"].abs() >= 0.05,
        canal["pnl"] / canal["r_at_exit"].replace(0, np.nan),
        np.nan,
    )
    fallback = float(np.nanmedian(canal["per_R_$"])) if canal["per_R_$"].notna().any() else 0.0
    canal["per_R_$"] = canal["per_R_$"].fillna(fallback)
    canal["delta_$"] = (canal["shadow_exit_r"] - canal["r_at_exit"]) * canal["per_R_$"]

    losers_recovered = (losers["shadow_exit_r"] >= 0).sum()

    return {
        "n_canal_exits": int(len(canal)),
        "n_with_shadow": int(shadow.notna().sum()),
        "mean_actual_R": round(float(actual.mean()), 3),
        "mean_shadow_R": round(float(shadow.mean()), 3),
        "median_actual_R": round(float(actual.median()), 3),
        "median_shadow_R": round(float(shadow.median()), 3),
        "delta_R_per_trade": round(float((shadow - actual).mean()), 3),
        "delta_$_per_trade": round(float(canal["delta_$"].mean()), 2),
        "total_delta_$_if_rule_applied": round(float(canal["delta_$"].sum()), 2),
        "losers_n": int(len(losers)),
        "losers_recovered_count": int(losers_recovered),
        "losers_recovered_pct": round(float(losers_recovered) / max(1, len(losers)) * 100.0, 1),
        "losers_actual_R": round(float(losers["r_at_exit"].mean()), 3),
        "losers_shadow_R": round(float(losers["shadow_exit_r"].mean()), 3),
        "winners_n": int(len(winners)),
        "winners_giveback_count": int((winners["shadow_exit_r"] < winners["r_at_exit"]).sum()),
        "winners_actual_R": round(float(winners["r_at_exit"].mean()), 3),
        "winners_shadow_R": round(float(winners["shadow_exit_r"].mean()), 3),
    }


def bars_since_setup_bucket(df: pd.DataFrame) -> pd.DataFrame:
    """How does position within the entry window affect outcome?

    bars_since_setup=0 → entered on the bar of the slow HMA/SSL cross itself.
    """
    d = df[df["bars_since_setup"] >= 0].copy()
    if d.empty:
        return pd.DataFrame()
    d["since_setup_bucket"] = pd.cut(
        d["bars_since_setup"], bins=[-1, 0, 1, 2, 3, 5, 8, 1e6],
        labels=["0", "1", "2", "3", "4-5", "6-8", ">8"]
    )
    g = d.groupby("since_setup_bucket", observed=True).agg(
        n=("pnl", "count"),
        pnl=("pnl", "sum"),
        avg_pnl=("pnl", "mean"),
        win_rate=("pnl", lambda s: float((s > 0).mean()) * 100.0),
        avg_r=("r_at_exit", "mean"),
        avg_bars=("bars_in_trade", "mean"),
    ).round(2).reset_index()
    return g


def side_split_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Per-side aggregates — most common hidden asymmetry."""
    g = df.groupby("side").agg(
        n=("pnl", "count"),
        pnl=("pnl", "sum"),
        avg_pnl=("pnl", "mean"),
        win_rate=("pnl", lambda s: float((s > 0).mean()) * 100.0),
        avg_r=("r_at_exit", "mean"),
        avg_mfe_r=("mfe_r", "mean"),
        avg_mae_r=("mae_r", "mean"),
        avg_bars=("bars_in_trade", "mean"),
    ).round(2).reset_index()
    return g


def side_status_breakdown(df: pd.DataFrame) -> pd.DataFrame:
    g = df.groupby(["side", "status"]).agg(
        n=("pnl", "count"),
        pnl=("pnl", "sum"),
        avg_pnl=("pnl", "mean"),
        win_rate=("pnl", lambda s: float((s > 0).mean()) * 100.0),
        avg_r=("r_at_exit", "mean"),
    ).round(2).reset_index()
    return g


def mfe_vs_outcome(df: pd.DataFrame) -> pd.DataFrame:
    """How much MFE existed before each SL?"""
    sl = df[df["status"].isin(["Stop Loss", "Breakeven"])].copy()
    if sl.empty:
        return pd.DataFrame()
    sl["mfe_bucket"] = pd.cut(sl["mfe_r"], bins=[-1, 0, 0.25, 0.5, 1.0, 2.0, 100],
                              labels=["≤0R", "0–0.25R", "0.25–0.5R", "0.5–1R", "1–2R", ">2R"])
    g = sl.groupby("mfe_bucket", observed=True).agg(
        n=("pnl", "count"),
        pnl=("pnl", "sum"),
        avg_pnl=("pnl", "mean"),
        avg_mae_r=("mae_r", "mean"),
    ).round(2).reset_index()
    return g


def slope_bucket_outcomes(df: pd.DataFrame) -> pd.DataFrame:
    """How does canal slope at entry correlate with outcome?"""
    d = df.dropna(subset=["canal_slope_pct_per_bar"]).copy()
    if d.empty:
        return pd.DataFrame()
    # Slope is signed; for shorts, "with-trend" means negative slope
    d["slope_with_trade"] = d.apply(
        lambda r: r["canal_slope_pct_per_bar"] * (1 if r["side"] == "Long" else -1), axis=1
    )
    d["slope_bucket"] = pd.cut(d["slope_with_trade"],
                                bins=[-1, -0.05, -0.01, 0.0, 0.01, 0.05, 1.0],
                                labels=["<-0.05%", "-0.05/-0.01%", "-0.01/0%",
                                        "0/0.01%", "0.01/0.05%", ">0.05%"])
    g = d.groupby("slope_bucket", observed=True).agg(
        n=("pnl", "count"),
        pnl=("pnl", "sum"),
        avg_pnl=("pnl", "mean"),
        win_rate=("pnl", lambda s: float((s > 0).mean()) * 100.0),
        avg_r=("r_at_exit", "mean"),
    ).round(2).reset_index()
    return g


def width_bucket_outcomes(df: pd.DataFrame) -> pd.DataFrame:
    d = df.dropna(subset=["canal_width_pct_e"]).copy()
    if d.empty:
        return pd.DataFrame()
    qs = d["canal_width_pct_e"].quantile([0.2, 0.4, 0.6, 0.8]).values
    edges = [-np.inf, *qs, np.inf]
    labels = ["Q1 narrow", "Q2", "Q3", "Q4", "Q5 wide"]
    d["width_bucket"] = pd.cut(d["canal_width_pct_e"], bins=edges, labels=labels)
    g = d.groupby("width_bucket", observed=True).agg(
        n=("pnl", "count"),
        pnl=("pnl", "sum"),
        avg_pnl=("pnl", "mean"),
        win_rate=("pnl", lambda s: float((s > 0).mean()) * 100.0),
        avg_r=("r_at_exit", "mean"),
    ).round(2).reset_index()
    return g


def sl_dist_bucket_outcomes(df: pd.DataFrame) -> pd.DataFrame:
    d = df.dropna(subset=["sl_dist_pct"]).copy()
    if d.empty:
        return pd.DataFrame()
    qs = d["sl_dist_pct"].quantile([0.2, 0.4, 0.6, 0.8]).values
    edges = [-np.inf, *qs, np.inf]
    labels = ["Q1 tight", "Q2", "Q3", "Q4", "Q5 wide"]
    d["sl_bucket"] = pd.cut(d["sl_dist_pct"], bins=edges, labels=labels)
    g = d.groupby("sl_bucket", observed=True).agg(
        n=("pnl", "count"),
        pnl=("pnl", "sum"),
        avg_pnl=("pnl", "mean"),
        win_rate=("pnl", lambda s: float((s > 0).mean()) * 100.0),
        avg_r=("r_at_exit", "mean"),
    ).round(2).reset_index()
    return g


def bars_in_trade_bucket(df: pd.DataFrame) -> pd.DataFrame:
    d = df.copy()
    d["bars_bucket"] = pd.cut(d["bars_in_trade"], bins=[-1, 1, 3, 6, 12, 24, 1e6],
                               labels=["≤1", "2-3", "4-6", "7-12", "13-24", ">24"])
    g = d.groupby("bars_bucket", observed=True).agg(
        n=("pnl", "count"),
        pnl=("pnl", "sum"),
        avg_pnl=("pnl", "mean"),
        win_rate=("pnl", lambda s: float((s > 0).mean()) * 100.0),
        avg_mfe_r=("mfe_r", "mean"),
        avg_mae_r=("mae_r", "mean"),
    ).round(2).reset_index()
    return g


def canal_color_consistency(df: pd.DataFrame) -> pd.DataFrame:
    """Compare trades entered with-color (HMA bull recent for long) vs opposite."""
    # canal_green_e=True means HMA stack is bullish at entry.
    # for a Long with canal_green_e=True → with-trend, for Long canal_green_e=False → counter-trend
    d = df.copy()
    d["with_trend"] = d.apply(
        lambda r: (r["canal_green_e"] and r["side"] == "Long") or
                  (not r["canal_green_e"] and r["side"] == "Short"), axis=1
    )
    g = d.groupby("with_trend").agg(
        n=("pnl", "count"),
        pnl=("pnl", "sum"),
        avg_pnl=("pnl", "mean"),
        win_rate=("pnl", lambda s: float((s > 0).mean()) * 100.0),
        avg_r=("r_at_exit", "mean"),
    ).round(2).reset_index()
    return g


def canal_flipped_outcome(df: pd.DataFrame) -> pd.DataFrame:
    d = df.copy()
    g = d.groupby("canal_flipped").agg(
        n=("pnl", "count"),
        pnl=("pnl", "sum"),
        avg_pnl=("pnl", "mean"),
        win_rate=("pnl", lambda s: float((s > 0).mean()) * 100.0),
        avg_r=("r_at_exit", "mean"),
    ).round(2).reset_index()
    return g


def hw_extreme_at_entry_bucket(df: pd.DataFrame) -> pd.DataFrame:
    d = df.dropna(subset=["hw_at_entry"]).copy()
    # For long: hw < extreme threshold means OK; we test bands of |hw|
    d["abs_hw"] = d["hw_at_entry"].abs()
    d["hw_bucket"] = pd.cut(d["abs_hw"], bins=[-1, 5, 10, 15, 20, 25, 30, 100],
                             labels=["0-5", "5-10", "10-15", "15-20", "20-25", "25-30", ">30"])
    g = d.groupby("hw_bucket", observed=True).agg(
        n=("pnl", "count"),
        pnl=("pnl", "sum"),
        avg_pnl=("pnl", "mean"),
        win_rate=("pnl", lambda s: float((s > 0).mean()) * 100.0),
        avg_r=("r_at_exit", "mean"),
    ).round(2).reset_index()
    return g


def first_hw_after_entry_bucket(df: pd.DataFrame) -> pd.DataFrame:
    """Group by how soon the first HW comes after entry."""
    d = df.dropna(subset=["first_hw_after_entry_bars"]).copy()
    d["hw_speed"] = pd.cut(d["first_hw_after_entry_bars"],
                            bins=[-1, 1, 2, 3, 5, 8, 12, 200],
                            labels=["1", "2", "3", "4-5", "6-8", "9-12", ">12"])
    g = d.groupby("hw_speed", observed=True).agg(
        n=("pnl", "count"),
        pnl=("pnl", "sum"),
        avg_pnl=("pnl", "mean"),
        win_rate=("pnl", lambda s: float((s > 0).mean()) * 100.0),
        avg_r=("r_at_exit", "mean"),
    ).round(2).reset_index()
    return g


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    all_dfs: List[pd.DataFrame] = []
    summaries: Dict[str, Any] = {}

    for preset_name, path in PRESETS.items():
        with open(path) as f:
            preset = json.load(f)
        print(f"\n=== Preset {preset_name} ({path.name}) ===")
        legs = _flatten(preset)
        preset_dfs = []
        for leg in legs:
            print(f"  → {leg['symbol']} {leg['interval']} risk={leg['risk']*100:.4f}%")
            run = run_leg(leg)
            df = analyze_leg(run)
            df["preset"] = preset_name
            preset_dfs.append(df)
            all_dfs.append(df)

        merged = pd.concat(preset_dfs, ignore_index=True) if preset_dfs else pd.DataFrame()
        merged.to_csv(OUT / f"trades_{preset_name}.csv", index=False)
        print(f"     → {OUT / f'trades_{preset_name}.csv'} ({len(merged)} trades)")

        summaries[preset_name] = {
            "n_trades": int(len(merged)),
            "net_pnl": round(float(merged["pnl"].sum()), 2),
            "win_rate": round(float((merged["pnl"] > 0).mean()) * 100.0, 2),
            "by_status": summary_by_status(merged).to_dict("records"),
            "hw_wait_one_more": hw_wait_one_more(merged),
            "mfe_vs_sl_outcome": mfe_vs_outcome(merged).to_dict("records"),
            "slope_buckets": slope_bucket_outcomes(merged).to_dict("records"),
            "width_buckets": width_bucket_outcomes(merged).to_dict("records"),
            "sl_dist_buckets": sl_dist_bucket_outcomes(merged).to_dict("records"),
            "bars_in_trade": bars_in_trade_bucket(merged).to_dict("records"),
            "canal_color_consistency": canal_color_consistency(merged).to_dict("records"),
            "canal_flipped": canal_flipped_outcome(merged).to_dict("records"),
            "hw_extreme_at_entry": hw_extreme_at_entry_bucket(merged).to_dict("records"),
            "first_hw_speed": first_hw_after_entry_bucket(merged).to_dict("records"),
            "bars_since_setup": bars_since_setup_bucket(merged).to_dict("records"),
            "side_split": side_split_summary(merged).to_dict("records"),
            "side_status": side_status_breakdown(merged).to_dict("records"),
        }

    # Combined dataset (all 3 presets concatenated)
    combined = pd.concat(all_dfs, ignore_index=True) if all_dfs else pd.DataFrame()
    combined.to_csv(OUT / "trades_ALL.csv", index=False)
    print(f"\n→ combined {OUT / 'trades_ALL.csv'} ({len(combined)} trades)")

    with open(OUT / "summary.json", "w") as f:
        json.dump(summaries, f, indent=2, default=str)
    print(f"→ summary {OUT / 'summary.json'}")

    # Print quick TLDR
    print("\n=== TLDR per preset ===")
    for name, s in summaries.items():
        print(f"\n{name}: n={s['n_trades']}  PnL=${s['net_pnl']:,.0f}  WR={s['win_rate']}%")
        print("  status breakdown:")
        for r in s["by_status"]:
            print(f"    {r['status']:<20s} n={r['n']:>4d}  PnL=${r['pnl']:>10,.0f}  "
                  f"avg=${r['avg_pnl']:>7,.1f}  WR={r['win_rate']:>5.1f}%  "
                  f"R={r['avg_r']:>5.2f}  bars={r['avg_bars']:>5.1f}")


if __name__ == "__main__":
    main()
