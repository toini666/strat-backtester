"""Phase 1 — observation déterministe des baselines V3.

Pour chaque baseline (MNQ_v5, MGC_v3) :
1. Replay déterministe (Lab strategy en defaults — confirmé equiv-V3 par sanity).
2. Pour chaque trade : MAE/MFE en R, bars_in_trade, bars_since_setup, hour,
   sl_distance_points, candle_pct, last_confirmed_hw_value, 2-bar body cumulé,
   distance R d'un shadow-exit au prochain HW.
3. Buckets winners/losers x pilier (A entry / B SL / C TP) pour chaque variable.
4. Écrit trades_<preset>.csv + trades_ALL.csv + summary.json.

OBSERVATIONS.md est rédigé manuellement à partir de ce summary.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

# Imports project-local
from scripts.goals._shared.harness import run_backtest  # noqa: E402
from scripts.goals._shared.preset import engine_from_dict  # noqa: E402
from src.data import market_store as ms_module  # noqa: E402
from src.data.market_store import SYMBOL_CONTRACTS  # noqa: E402
from src.engine.simulator import _to_ref_minutes  # noqa: E402

# Repo-local baselines (mirror of _shared.py).
HERE = Path(__file__).resolve().parent
OUT = HERE / "outputs"
OUT.mkdir(parents=True, exist_ok=True)

BASELINES = {
    "MNQ_v5": ROOT / "scripts/goals/2026-05-17_HMASSLOsciV3_MNQ_v5/winner_preset.json",
    "MGC_v3": ROOT / "scripts/goals/2026-05-17_HMASSLOsciV3_MGC_v3/winner_preset.json",
}


# ---------------------------------------------------------------------------
# Backtest replay with full indicator dump
# ---------------------------------------------------------------------------


def replay_with_signals(preset_path: Path):
    preset = json.loads(Path(preset_path).read_text())
    engine = engine_from_dict(preset["engineSettings"])
    overrides = {k: v for k, v in preset["params"].items() if k != "tick_size"}

    # Use the original V3 (faster, fewer params) — Lab is equiv (sanity passed).
    result = run_backtest(
        strategy_name=preset["strategyName"],
        symbol=preset["symbol"],
        interval=preset["interval"],
        start=preset["startDatetime"],
        end=preset["endDatetime"],
        strategy_params=overrides,
        initial_equity=preset["initialEquity"],
        risk_per_trade=preset["riskPerTrade"] / 100.0,
        max_contracts=preset["maxContracts"],
        engine_settings=engine,
    )

    # We also need the indicator/signal frame and the 1m data for MAE/MFE.
    # Replay the strategy alone to extract the debug_frame & signals.
    from backend.api import (
        STRATEGIES,
        STRATEGY_WARMUP_BARS,
        DEFAULT_WARMUP_BARS,
        _annotate_blackout_flags,
        _build_blackout_windows,
        _contract_backtest_specs,
        _normalize_backtest_datetime,
        _slice_from_start,
        load_strategies,
    )
    from datetime import timedelta

    load_strategies()
    strat_cls = STRATEGIES[preset["strategyName"]]
    contract_id = SYMBOL_CONTRACTS[preset["symbol"]]
    specs = _contract_backtest_specs(preset["symbol"])

    original_start = _normalize_backtest_datetime(preset["startDatetime"])
    end_date = _normalize_backtest_datetime(preset["endDatetime"])
    warmup = STRATEGY_WARMUP_BARS.get(preset["strategyName"], DEFAULT_WARMUP_BARS)

    interval = preset["interval"]
    map_min = {"1m": 1, "2m": 2, "3m": 3, "5m": 5, "7m": 7, "10m": 10, "15m": 15}
    minutes_per_bar = map_min.get(interval, 15)
    trading_minutes_needed = warmup * minutes_per_bar
    trading_days = trading_minutes_needed / (23 * 60)
    calendar_days = max(2, int(trading_days * 7 / 5) + 3)
    start_with_warmup = original_start - timedelta(days=calendar_days)

    ds_meta = ms_module.MarketDataStore().get_dataset_by_symbol(preset["symbol"])
    if ds_meta:
        ds_start = pd.Timestamp(ds_meta["start_date"])
        if ds_start.tzinfo is None:
            ds_start = ds_start.tz_localize("Europe/Brussels")
        if start_with_warmup < ds_start:
            start_with_warmup = ds_start

    store = ms_module.MarketDataStore()
    data = store.load_bars(contract_id, start_with_warmup, end_date, interval)
    data_1m = store.load_bars(contract_id, start_with_warmup, end_date, "1m")

    strat = strat_cls()
    params = dict(strat_cls.default_params)
    params.update(overrides)
    params["tick_size"] = specs["tick_size"]
    blackouts = _build_blackout_windows(engine)
    annotated = _annotate_blackout_flags(data, blackouts)
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

    # `setup_bar_long/short` values reference positions in the FULL (warmup+actual)
    # data. To convert to a sliced position: subtract this offset.
    # mask may be a numpy bool array or a Series — handle both.
    mask_arr = mask.values if hasattr(mask, "values") else mask
    warmup_offset = int(mask_arr.argmax())  # number of False before first True

    return preset, result, sliced, sliced_signals, data_1m_sliced, warmup_offset


# ---------------------------------------------------------------------------
# Per-trade enrichment: MAE/MFE, bars in trade, entry context
# ---------------------------------------------------------------------------


def enrich_trades(
    *,
    trades: list,
    data: pd.DataFrame,
    data_1m: pd.DataFrame,
    signals: dict,
    tick_size: float,
    warmup_offset: int = 0,
) -> pd.DataFrame:
    """One row per trade with computed MAE/MFE in R + entry-bar indicator state."""
    debug = signals.get("debug_frame")
    setup_long = signals["setup_bar_long"]
    setup_short = signals["setup_bar_short"]
    sl_long = signals["sl_long"]
    sl_short = signals["sl_short"]
    hw_over = signals["hw_cross_over"]
    hw_under = signals["hw_cross_under"]
    canal_lower = signals["canal_lower"]
    canal_upper = signals["canal_upper"]
    canal_green = signals["canal_green"]

    # Pre-index data for fast lookup.
    idx = data.index
    idx_pos = {ts: i for i, ts in enumerate(idx)}
    idx_1m = data_1m.index

    open_ = data["Open"].values
    close = data["Close"].values

    rows = []
    for t in trades:
        if t.get("excluded"):
            continue
        et = pd.Timestamp(t["entry_time"])
        xt = pd.Timestamp(t["exit_time"])
        if et.tzinfo is None:
            et = et.tz_localize("Europe/Brussels")
        if xt.tzinfo is None:
            xt = xt.tz_localize("Europe/Brussels")
        if et not in idx_pos:
            # rare bar-alignment issue — skip
            continue
        ei = idx_pos[et]

        side = 1 if t["side"] == "Long" else -1
        entry_price = t["entry_price"]
        # SL at entry bar (strategy emits the SL series; pick the entry bar's value)
        sl_at_entry = sl_long.iloc[ei] if side == 1 else sl_short.iloc[ei]
        if pd.isna(sl_at_entry):
            # If the SL is missing (e.g. sl_full was overwritten), reconstruct
            # from the trade's stop distance (entry → sl_at_entry from result not in trade).
            continue
        risk_dist = abs(entry_price - sl_at_entry)
        if risk_dist <= 0:
            continue

        # MAE/MFE on 1m bars between entry exec and exit exec.
        # Use entry_execution_time and exit_execution_time (string) when present.
        ee = pd.Timestamp(t.get("entry_execution_time") or t["entry_time"])
        xe = pd.Timestamp(t.get("exit_execution_time") or t["exit_time"])
        if ee.tzinfo is None:
            ee = ee.tz_localize("Europe/Brussels")
        if xe.tzinfo is None:
            xe = xe.tz_localize("Europe/Brussels")
        mask = (idx_1m >= ee) & (idx_1m <= xe)
        sub = data_1m.loc[mask]
        if len(sub) == 0:
            mae_pts = 0.0
            mfe_pts = 0.0
            bars_1m = 0
        else:
            if side == 1:
                # Adverse = min(low) below entry; favorable = max(high) above entry.
                mae_pts = entry_price - sub["Low"].min()
                mfe_pts = sub["High"].max() - entry_price
            else:
                mae_pts = sub["High"].max() - entry_price
                mfe_pts = entry_price - sub["Low"].min()
            bars_1m = len(sub)
        # Clamp at 0 (entry-bar tick can be marginally above/below).
        mae_pts = max(0.0, float(mae_pts))
        mfe_pts = max(0.0, float(mfe_pts))
        mae_r = mae_pts / risk_dist
        mfe_r = mfe_pts / risk_dist

        # Bars in trade (TF bars between entry_time and exit_time)
        xi = idx_pos.get(xt, ei)
        bars_in_trade = xi - ei

        # Bars since setup. `setup_long/short` values are positions in the FULL
        # (warmup+actual) data; ei is a position in the sliced data. Convert
        # FULL position → sliced position by subtracting warmup_offset.
        sl_bar_full = setup_long.iloc[ei] if side == 1 else setup_short.iloc[ei]
        if sl_bar_full is not None and sl_bar_full >= 0:
            sl_bar_sliced = int(sl_bar_full) - warmup_offset
            bars_since_setup = ei - sl_bar_sliced
            # If the setup happened during warmup (negative sliced), clip to 0
            if bars_since_setup < 0:
                bars_since_setup = -1
        else:
            bars_since_setup = -1

        # Hour of day (reference Brussels)
        ref_min = _to_ref_minutes(et)
        hour = (ref_min // 60) % 24

        # Candle pct (single bar) & 2-bar cumulative body
        o = float(open_[ei]); c = float(close[ei])
        body0 = abs(c - o)
        body1 = abs(close[ei - 1] - open_[ei - 1]) if ei > 0 else 0.0
        cp1 = (body0 / c * 100.0) if c else np.nan
        cp2 = ((body0 + body1) / c * 100.0) if c else np.nan

        # Indicator context (from debug frame)
        if debug is not None and et in debug.index:
            row_d = debug.loc[et]
            last_hw_val = float(row_d["last_confirmed_hw_value"])
            osc_sig = float(row_d["osc_sig"]) if not pd.isna(row_d["osc_sig"]) else np.nan
            mfi_val = float(row_d["mfi"]) if not pd.isna(row_d["mfi"]) else np.nan
            cg = bool(row_d["canal_green"])
            cu = float(row_d["canal_upper"]) if not pd.isna(row_d["canal_upper"]) else np.nan
            cl = float(row_d["canal_lower"]) if not pd.isna(row_d["canal_lower"]) else np.nan
            canal_width = (cu - cl) if not (np.isnan(cu) or np.isnan(cl)) else np.nan
        else:
            last_hw_val = np.nan; osc_sig = np.nan; mfi_val = np.nan
            cg = canal_green.iloc[ei] if ei in range(len(canal_green)) else False
            canal_width = np.nan

        # Shadow exit at next favorable HW cross
        hw_window = hw_under.iloc[ei + 1 :] if side == 1 else hw_over.iloc[ei + 1 :]
        nxt_hw = hw_window.idxmax() if hw_window.any() else None
        shadow_bars = (idx_pos[nxt_hw] - ei) if nxt_hw is not None and nxt_hw in idx_pos else -1

        # Status simplification
        status = t["status"]
        kind = "winner" if t["pnl"] > 0 else ("loser" if t["pnl"] < 0 else "scratch")

        rows.append({
            "entry_time": et,
            "exit_time": xt,
            "side": "Long" if side == 1 else "Short",
            "status": status,
            "pnl": float(t["pnl"]),
            "size": float(t["size"]),
            "kind": kind,
            "entry_price": entry_price,
            "exit_price": float(t["exit_price"]),
            "risk_dist_points": risk_dist,
            "mae_pts": mae_pts,
            "mfe_pts": mfe_pts,
            "mae_r": mae_r,
            "mfe_r": mfe_r,
            "bars_in_trade": int(bars_in_trade),
            "bars_since_setup": int(bars_since_setup),
            "hour": int(hour),
            "candle_pct": cp1,
            "two_bar_body_pct": cp2,
            "last_hw_value": last_hw_val,
            "osc_sig": osc_sig,
            "mfi": mfi_val,
            "canal_green": int(cg),
            "canal_width": canal_width,
            "shadow_hw_bars": int(shadow_bars),
        })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Bucketing winners vs losers
# ---------------------------------------------------------------------------


def bucket_split(df: pd.DataFrame, var: str, q: int = 5) -> pd.DataFrame:
    """Split var into q quantile-buckets and compute winners vs losers per bucket."""
    if df[var].notna().sum() < q * 2:
        return pd.DataFrame()
    bins = pd.qcut(df[var], q=q, duplicates="drop")
    agg = (
        df.assign(bucket=bins)
        .groupby("bucket", observed=True)
        .agg(
            n=("pnl", "size"),
            wins=("pnl", lambda x: (x > 0).sum()),
            losses=("pnl", lambda x: (x < 0).sum()),
            pnl=("pnl", "sum"),
            avg_pnl=("pnl", "mean"),
            avg_mae_r=("mae_r", "mean"),
            avg_mfe_r=("mfe_r", "mean"),
        )
        .reset_index()
    )
    agg["wr"] = agg["wins"] / agg["n"] * 100.0
    agg["bucket"] = agg["bucket"].astype(str)
    return agg


def discrete_split(df: pd.DataFrame, var: str) -> pd.DataFrame:
    agg = (
        df.groupby(var, observed=True)
        .agg(
            n=("pnl", "size"),
            wins=("pnl", lambda x: (x > 0).sum()),
            losses=("pnl", lambda x: (x < 0).sum()),
            pnl=("pnl", "sum"),
            avg_pnl=("pnl", "mean"),
            avg_mae_r=("mae_r", "mean"),
            avg_mfe_r=("mfe_r", "mean"),
        )
        .reset_index()
    )
    agg["wr"] = agg["wins"] / agg["n"] * 100.0
    return agg


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    all_dfs = []
    summary: dict = {"per_preset": {}}

    for label, path in BASELINES.items():
        print(f"\n[{label}] replaying and enriching trades …")
        preset, result, data, signals, data_1m, warmup_offset = replay_with_signals(path)
        tick = preset["params"]["tick_size"]
        df = enrich_trades(
            trades=result["trades"],
            data=data, data_1m=data_1m, signals=signals,
            tick_size=tick,
            warmup_offset=warmup_offset,
        )
        df["preset"] = label
        out_csv = OUT / f"trades_{label}.csv"
        df.to_csv(out_csv, index=False)
        print(f"   → {out_csv} ({len(df)} active trades)")

        # Per-preset summary blocks
        block: dict = {}
        block["n_active"] = int(len(df))
        block["n_wins"] = int((df["pnl"] > 0).sum())
        block["n_losses"] = int((df["pnl"] < 0).sum())
        block["total_pnl"] = round(float(df["pnl"].sum()), 2)
        block["mae_r_mean_winners"] = round(float(df.query("kind=='winner'")["mae_r"].mean() or 0), 3)
        block["mae_r_mean_losers"] = round(float(df.query("kind=='loser'")["mae_r"].mean() or 0), 3)
        block["mfe_r_mean_winners"] = round(float(df.query("kind=='winner'")["mfe_r"].mean() or 0), 3)
        block["mfe_r_mean_losers"] = round(float(df.query("kind=='loser'")["mfe_r"].mean() or 0), 3)

        # Status breakdown
        block["status_breakdown"] = (
            df.groupby("status")["pnl"]
            .agg(["count", "sum", "mean"])
            .reset_index()
            .to_dict(orient="records")
        )

        # Buckets by var — all in summary.json (OBSERVATIONS.md reads from here)
        for var in ["bars_since_setup", "hour", "side"]:
            block[f"by_{var}"] = discrete_split(df, var).to_dict(orient="records")
        for var, q in [
            ("candle_pct", 5),
            ("two_bar_body_pct", 5),
            ("risk_dist_points", 5),
            ("last_hw_value", 5),
            ("canal_width", 5),
        ]:
            block[f"by_{var}"] = bucket_split(df, var, q=q).to_dict(orient="records")

        summary["per_preset"][label] = block
        all_dfs.append(df)

    if all_dfs:
        all_df = pd.concat(all_dfs, ignore_index=True)
        out_csv = OUT / "trades_ALL.csv"
        all_df.to_csv(out_csv, index=False)
        print(f"\nMerged: {out_csv} ({len(all_df)} trades)")

    out_json = OUT / "summary.json"
    out_json.write_text(json.dumps(summary, indent=2, default=str))
    print(f"Summary: {out_json}")


if __name__ == "__main__":
    main()
