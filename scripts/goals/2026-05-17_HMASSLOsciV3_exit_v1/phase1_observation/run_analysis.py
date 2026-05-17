"""Phase 1 — dissection of V3 exits.

For each reference preset, replays the V3 backtest and dumps a per-trade CSV
enriched with exit-mechanism diagnostics:

  - exit reason (status / leg statuses)
  - bars between entry and first fast HMA cross
  - bars between fast cross and the actual exit (= HW confirmation wait)
  - PnL at fast cross (shadow) vs PnL at real exit, and the delta
  - MFE / MAE in R-units between entry and exit
  - canal_green at fast cross and at exit
  - shadow PnL at first contra HMA flip after entry

Outputs:
  - exits_<preset>.csv  per-trade rows
  - exits_ALL.csv       concatenated across presets
  - summary.json        bucketed aggregates feeding OBSERVATIONS.md
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from backend.api import (  # noqa: E402
    BACKTEST_TZ,
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
from datetime import timedelta  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "phase2_hypotheses"))
from _shared import BASELINES, load_preset, strategy_params  # noqa: E402

from scripts.goals._shared.preset import engine_from_dict  # noqa: E402


def run_and_capture(preset: dict) -> Dict[str, Any]:
    """Run V3 baseline and return everything we need for dissection."""
    load_strategies()
    strat_name = "HMASSLOsciV3"
    strat_cls = STRATEGIES[strat_name]
    symbol = preset["symbol"]
    interval = preset["interval"]
    contract_id = SYMBOL_CONTRACTS[symbol]
    specs = _contract_backtest_specs(symbol)
    engine = engine_from_dict(preset["engineSettings"])
    p = strategy_params(preset)
    p["tick_size"] = specs["tick_size"]

    original_start = _normalize_backtest_datetime(preset["startDatetime"])
    end_date = _normalize_backtest_datetime(preset["endDatetime"])
    warmup = STRATEGY_WARMUP_BARS.get(strat_name, DEFAULT_WARMUP_BARS)

    map_min = {"1m": 1, "2m": 2, "3m": 3, "5m": 5, "7m": 7, "10m": 10, "15m": 15}
    minutes_per_bar = map_min.get(interval, 15)
    trading_minutes_needed = warmup * minutes_per_bar
    trading_days = trading_minutes_needed / (23 * 60)
    calendar_days = max(2, int(trading_days * 7 / 5) + 3)
    start_date = original_start - timedelta(days=calendar_days)

    ds_meta = ms_module.MarketDataStore().get_dataset_by_symbol(symbol)
    if ds_meta:
        ds_start = pd.Timestamp(ds_meta["start_date"])
        if ds_start.tzinfo is None:
            ds_start = ds_start.tz_localize(BACKTEST_TZ)
        if start_date < ds_start:
            start_date = ds_start

    store = ms_module.MarketDataStore()
    data = store.load_bars(contract_id, start_date, end_date, interval)
    data_1m = store.load_bars(contract_id, start_date, end_date, "1m")

    strat = strat_cls()
    sim_settings = strat.get_simulator_settings(p)
    blackout_windows = _build_blackout_windows(engine)
    annotated = _annotate_blackout_flags(data, blackout_windows)
    signals = strat.generate_signals(annotated, p)

    sliced, mask = _slice_from_start(data, original_start)
    sliced_signals: Dict[str, Any] = {}
    for k, v in signals.items():
        if isinstance(v, pd.Series):
            sliced_signals[k] = v.loc[mask]
        elif isinstance(v, pd.DataFrame):
            sliced_signals[k] = v.loc[mask]
        else:
            sliced_signals[k] = v
    data_1m_sliced, _ = _slice_from_start(data_1m, original_start)

    cfg = SimulatorConfig(
        initial_equity=preset["initialEquity"],
        risk_per_trade=preset["riskPerTrade"] / 100.0,
        max_contracts=preset["maxContracts"],
        tick_size=specs["tick_size"],
        tick_value=specs["tick_value"],
        point_value=specs["point_value"],
        fee_per_trade=specs["fee_per_trade"],
        auto_close_enabled=engine.auto_close_enabled,
        auto_close_hour=engine.auto_close_hour,
        auto_close_minute=engine.auto_close_minute,
        blackout_windows=blackout_windows,
        cooldown_bars=int(sliced_signals.get("cooldown_bars", p.get("cooldown_bars", 0))),
        tp1_execution_mode=str(sim_settings.get("tp1_execution_mode", "touch")),
        tp1_partial_pct=float(sim_settings.get("tp1_partial_pct", 0.25)),
        tp2_partial_pct=float(sim_settings.get("tp2_partial_pct", 0.25)),
        ema_exit_after_tp1_only=bool(sim_settings.get("ema_exit_after_tp1_only", False)),
        no_sl_after_tp1=bool(sim_settings.get("no_sl_after_tp1", False)),
        tp1_full_exit=bool(sim_settings.get("tp1_full_exit", False)),
        inverse_canal_exit=bool(sim_settings.get("inverse_canal_exit", False)),
        canal_exit_mode=str(sim_settings.get("canal_exit_mode", "break_hma")),
        block_loss_canal_exit_before_tp1=bool(sim_settings.get("block_loss_canal_exit_before_tp1", False)),
        close_partial_min_rr=float(sim_settings.get("close_partial_min_rr", 0.0)),
        one_trade_per_setup_window=bool(sim_settings.get("one_trade_per_setup_window", False)),
        final_exit_pct=float(sim_settings.get("final_exit_pct", 0.0)),
        daily_win_limit_enabled=engine.daily_win_limit_enabled,
        daily_win_limit=engine.daily_win_limit,
        daily_loss_limit_enabled=engine.daily_loss_limit_enabled,
        daily_loss_limit=engine.daily_loss_limit,
        daily_limit_mode=engine.daily_limit_mode,
    )
    result = simulate_strategy(
        data=sliced,
        data_1m=data_1m_sliced,
        signals=sliced_signals,
        config=cfg,
        ema_main=sliced_signals["ema_main"],
        ema_secondary=sliced_signals["ema_secondary"],
    )
    return {
        "data": sliced,
        "signals": sliced_signals,
        "trades": result["trades"],
        "metrics": result["metrics"],
        "specs": specs,
        "initial_equity": preset["initialEquity"],
        "risk_per_trade": preset["riskPerTrade"] / 100.0,
    }


def dissect_trades(captured: Dict[str, Any], preset_name: str) -> pd.DataFrame:
    data: pd.DataFrame = captured["data"]
    s: Dict[str, Any] = captured["signals"]
    trades: List[dict] = captured["trades"]
    specs = captured["specs"]

    np_close = data["Close"].values
    np_high = data["High"].values
    np_low = data["Low"].values
    idx = data.index

    fast_l = s["fast_hma_exit_long"].values.astype(bool)
    fast_s = s["fast_hma_exit_short"].values.astype(bool)
    hw_over = s["hw_cross_over"].values.astype(bool)
    hw_under = s["hw_cross_under"].values.astype(bool)
    canal_green = s["canal_green"].values.astype(bool)
    flip_up = s["hma_flip_up"].values.astype(bool)
    flip_down = s["hma_flip_down"].values.astype(bool)
    sl_long_arr = s["sl_long"].values
    sl_short_arr = s["sl_short"].values

    point_value = specs["point_value"]
    tick_value = specs["tick_value"]
    tick_size = specs["tick_size"]

    def time_to_bar(t: str) -> int:
        ts = pd.Timestamp(t)
        if ts.tzinfo is None:
            ts = ts.tz_localize(BACKTEST_TZ)
        try:
            return idx.get_loc(ts)
        except KeyError:
            return int(np.searchsorted(idx, ts))

    def find_first_after(arr: np.ndarray, after_bar: int, max_lookahead: int = 500) -> int | None:
        end = min(len(arr), after_bar + max_lookahead + 1)
        for j in range(after_bar + 1, end):
            if arr[j]:
                return j
        return None

    rows = []
    for t in trades:
        if t.get("excluded"):
            continue
        side = 1 if t["side"].lower() == "long" else -1
        entry_bar = time_to_bar(t["entry_time"])
        exit_bar = time_to_bar(t["exit_time"])
        entry_price = float(t["entry_price"])
        exit_price = float(t["exit_price"])
        size = float(t["size"])
        pnl_real = float(t["pnl"])
        status = t.get("status", "")
        # Status of the last leg captures the exit reason
        last_leg_status = (t["legs"][-1]["status"] if t.get("legs") else status) or status

        # Find first fast cross after entry (in trade direction = contra-trade)
        fast_arr = fast_l if side == 1 else fast_s
        first_fast_bar = find_first_after(fast_arr, entry_bar, max_lookahead=exit_bar - entry_bar + 50)
        # Restrict to fast cross within trade lifetime (≤ exit_bar)
        if first_fast_bar is not None and first_fast_bar > exit_bar:
            first_fast_bar = None

        # First HW cross after the fast cross (any side)
        first_hw_bar = None
        if first_fast_bar is not None:
            hw_any = hw_over | hw_under
            j = find_first_after(hw_any, first_fast_bar - 1, max_lookahead=exit_bar - first_fast_bar + 50)
            if j is not None and j <= exit_bar:
                first_hw_bar = j

        # First canal flip in contra direction after entry
        contra_flip = flip_down if side == 1 else flip_up
        first_flip_bar = find_first_after(contra_flip, entry_bar, max_lookahead=exit_bar - entry_bar + 50)
        if first_flip_bar is not None and first_flip_bar > exit_bar:
            first_flip_bar = None

        # SL distance used for R-units
        sl_at_entry = sl_long_arr[entry_bar] if side == 1 else sl_short_arr[entry_bar]
        risk_pts = (entry_price - sl_at_entry) if side == 1 else (sl_at_entry - entry_price)
        risk_pts = float(risk_pts) if not np.isnan(risk_pts) else np.nan

        # MFE / MAE in R-units
        seg_high = np_high[entry_bar:exit_bar + 1] if exit_bar >= entry_bar else np.array([])
        seg_low = np_low[entry_bar:exit_bar + 1] if exit_bar >= entry_bar else np.array([])
        if len(seg_high) > 0 and risk_pts and risk_pts > 0:
            if side == 1:
                mfe_r = (seg_high.max() - entry_price) / risk_pts
                mae_r = (seg_low.min() - entry_price) / risk_pts  # negative = adverse
            else:
                mfe_r = (entry_price - seg_low.min()) / risk_pts
                mae_r = (entry_price - seg_high.max()) / risk_pts  # negative = adverse
        else:
            mfe_r = np.nan
            mae_r = np.nan

        # Shadow PnL at fast cross (in $ on this trade's size)
        def pnl_at_bar(bar: int) -> float | None:
            if bar is None:
                return None
            close = np_close[bar]
            pts = (close - entry_price) if side == 1 else (entry_price - close)
            return pts * point_value * size - 2 * specs["fee_per_trade"] * size

        pnl_at_fast = pnl_at_bar(first_fast_bar)
        pnl_at_hw = pnl_at_bar(first_hw_bar)
        pnl_at_flip = pnl_at_bar(first_flip_bar)

        # Delta HW − fast (positive = HW wait paid; negative = it cost)
        if pnl_at_hw is not None and pnl_at_fast is not None:
            delta_hw_minus_fast = pnl_at_hw - pnl_at_fast
        else:
            delta_hw_minus_fast = None

        # Canal_green at fast and at exit
        cg_at_fast = bool(canal_green[first_fast_bar]) if first_fast_bar is not None else None
        cg_at_exit = bool(canal_green[exit_bar])

        # "Give-back" indicator: MFE positive but pnl_real negative
        gave_back = (mfe_r is not None and not np.isnan(mfe_r) and mfe_r >= 0.5 and pnl_real < 0)

        rows.append({
            "preset": preset_name,
            "entry_time": t["entry_time"],
            "exit_time": t["exit_time"],
            "side": t["side"],
            "size": size,
            "entry_bar": entry_bar,
            "exit_bar": exit_bar,
            "bars_in_trade": exit_bar - entry_bar,
            "entry_price": entry_price,
            "exit_price": exit_price,
            "pnl_real": round(pnl_real, 2),
            "status": status,
            "last_leg_status": last_leg_status,
            "risk_pts": round(risk_pts, 4) if not np.isnan(risk_pts) else None,
            "mfe_r": round(mfe_r, 3) if not np.isnan(mfe_r) else None,
            "mae_r": round(mae_r, 3) if not np.isnan(mae_r) else None,
            "first_fast_cross_bar": first_fast_bar,
            "first_hw_after_fast_bar": first_hw_bar,
            "first_contra_flip_bar": first_flip_bar,
            "bars_fast_to_exit": (exit_bar - first_fast_bar) if first_fast_bar is not None else None,
            "bars_fast_to_hw": (first_hw_bar - first_fast_bar) if (first_hw_bar is not None and first_fast_bar is not None) else None,
            "pnl_at_fast_cross": round(pnl_at_fast, 2) if pnl_at_fast is not None else None,
            "pnl_at_hw_cross": round(pnl_at_hw, 2) if pnl_at_hw is not None else None,
            "pnl_at_canal_flip": round(pnl_at_flip, 2) if pnl_at_flip is not None else None,
            "delta_hw_minus_fast": round(delta_hw_minus_fast, 2) if delta_hw_minus_fast is not None else None,
            "delta_flip_minus_real": round(pnl_at_flip - pnl_real, 2) if pnl_at_flip is not None else None,
            "canal_green_at_fast": cg_at_fast,
            "canal_green_at_exit": cg_at_exit,
            "gave_back_after_mfe": gave_back,
            "hour_of_entry": pd.Timestamp(t["entry_time"]).hour,
            "hour_of_exit": pd.Timestamp(t["exit_time"]).hour,
        })
    return pd.DataFrame(rows)


def summarize_population(df: pd.DataFrame, label: str) -> Dict[str, Any]:
    n = len(df)
    out = {
        "label": label,
        "n_trades": n,
        "net_pnl_real": round(df["pnl_real"].sum(), 2),
    }
    # Where fast and hw bars both available, look at delta(hw - fast) distribution
    sub = df.dropna(subset=["delta_hw_minus_fast"])
    if len(sub) > 0:
        out["n_with_fast_then_hw"] = len(sub)
        out["mean_delta_hw_minus_fast"] = round(sub["delta_hw_minus_fast"].mean(), 2)
        out["median_delta_hw_minus_fast"] = round(sub["delta_hw_minus_fast"].median(), 2)
        out["pct_hw_paid"] = round(100 * (sub["delta_hw_minus_fast"] > 0).mean(), 1)
        out["pct_hw_cost"] = round(100 * (sub["delta_hw_minus_fast"] < 0).mean(), 1)
        out["pct_hw_neutral"] = round(100 * (sub["delta_hw_minus_fast"].abs() < 1).mean(), 1)
        out["sum_delta_hw_minus_fast"] = round(sub["delta_hw_minus_fast"].sum(), 2)
        # Conditional: when fast was in profit
        fast_in_profit = sub[sub["pnl_at_fast_cross"] > 0]
        if len(fast_in_profit) > 0:
            out["n_fast_in_profit"] = len(fast_in_profit)
            out["mean_delta_when_fast_in_profit"] = round(fast_in_profit["delta_hw_minus_fast"].mean(), 2)
        fast_in_loss = sub[sub["pnl_at_fast_cross"] <= 0]
        if len(fast_in_loss) > 0:
            out["n_fast_in_loss"] = len(fast_in_loss)
            out["mean_delta_when_fast_in_loss"] = round(fast_in_loss["delta_hw_minus_fast"].mean(), 2)

    # Canal flip alt path
    cf = df.dropna(subset=["pnl_at_canal_flip"])
    if len(cf) > 0:
        out["n_with_contra_flip_in_trade"] = len(cf)
        out["mean_pnl_at_canal_flip"] = round(cf["pnl_at_canal_flip"].mean(), 2)
        out["mean_pnl_real_for_flip_subset"] = round(cf["pnl_real"].mean(), 2)
        out["sum_delta_flip_alt_minus_real"] = round((cf["pnl_at_canal_flip"] - cf["pnl_real"]).sum(), 2)

    # Give-back stats
    out["n_gave_back"] = int(df["gave_back_after_mfe"].sum())
    out["pct_gave_back"] = round(100 * df["gave_back_after_mfe"].mean(), 1)
    # Of give-backs: what was the max MFE?
    gb = df[df["gave_back_after_mfe"]]
    if len(gb) > 0:
        out["gave_back_mean_mfe_r"] = round(gb["mfe_r"].mean(), 2)
        out["gave_back_mean_pnl_real"] = round(gb["pnl_real"].mean(), 2)

    # MFE distribution among final-positive vs final-negative
    win = df[df["pnl_real"] > 0]
    lose = df[df["pnl_real"] < 0]
    if len(win) > 0:
        out["wins_mean_mfe_r"] = round(win["mfe_r"].mean(skipna=True), 2)
        out["wins_n_with_mfe_ge_1r"] = int((win["mfe_r"] >= 1.0).sum())
    if len(lose) > 0:
        out["losses_mean_mfe_r"] = round(lose["mfe_r"].mean(skipna=True), 2)
        out["losses_n_with_mfe_ge_1r"] = int((lose["mfe_r"] >= 1.0).sum())
        out["losses_pct_with_mfe_ge_1r"] = round(100 * (lose["mfe_r"] >= 1.0).mean(), 1)

    return out


def main():
    out_dir = Path(__file__).resolve().parent / "outputs"
    out_dir.mkdir(parents=True, exist_ok=True)
    all_rows = []
    summaries = {}
    for name, path in BASELINES.items():
        print(f"\n=== Dissecting {name} ({path.name}) ===")
        preset = load_preset(path)
        captured = run_and_capture(preset)
        df = dissect_trades(captured, name)
        df.to_csv(out_dir / f"exits_{name}.csv", index=False)
        summary = summarize_population(df, name)
        # Also bucket by side
        for side_label, sub in [("LONG", df[df["side"].str.lower() == "long"]),
                                 ("SHORT", df[df["side"].str.lower() == "short"])]:
            if len(sub) > 0:
                summary[f"by_side_{side_label}"] = summarize_population(sub, f"{name}_{side_label}")
        # Bucket by canal_green at fast (regime)
        for cg_label, sub in [("FAST_IN_GREEN", df[df["canal_green_at_fast"] == True]),
                               ("FAST_IN_RED", df[df["canal_green_at_fast"] == False])]:
            if len(sub) > 0:
                summary[f"by_regime_{cg_label}"] = summarize_population(sub, f"{name}_{cg_label}")
        summaries[name] = summary
        all_rows.append(df)
        print(f"  N={len(df)} trades; "
              f"net=${df['pnl_real'].sum():,.0f}; "
              f"gave_back={summary['n_gave_back']} ({summary['pct_gave_back']}%); "
              f"hw_paid={summary.get('pct_hw_paid', 'n/a')}%; "
              f"hw_cost={summary.get('pct_hw_cost', 'n/a')}%")

    df_all = pd.concat(all_rows, ignore_index=True)
    df_all.to_csv(out_dir / "exits_ALL.csv", index=False)
    summaries["ALL"] = summarize_population(df_all, "ALL")
    (out_dir / "summary.json").write_text(json.dumps(summaries, indent=2, default=str))
    print(f"\nOutputs in {out_dir.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
