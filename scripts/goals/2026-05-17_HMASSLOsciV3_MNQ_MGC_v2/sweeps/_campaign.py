"""Campaign-local constants & helpers — MNQ+MGC v2 (starting from NEW preset).

Goal: drive DD below $2,000 while keeping PnL > $100k.

Starting point: preset "Multi-Asset — MNQ/MGC - NEW" in data/presets.json
- MNQ: mf_length=31, mf_smooth=7, cooldown_bars=3, max_sl_points=300, risk=0.48%
       blackouts active: 22-23:59, 11-12, 14-15, 8-9, 12-13
- MGC: mf_length=29, mf_smooth=5, cloud_on=True, risk=0.52%
       blackouts active: 22-23:59, 11-12, 6-7, 7-8, 3-4, 9-10
"""
from __future__ import annotations

import sys
import time
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.api import (  # noqa: E402
    BacktestEngineSettings,
    BlackoutWindowSettings,
    _apply_combined_daily_limits,
)
from scripts.goals._shared.harness import run_backtest  # noqa: E402

STRATEGY = "HMASSLOsciV3"
INTERVAL = "7m"
START = "2025-01-06T00:00"
END = "2026-05-15T00:00"
INITIAL_EQUITY = 50_000.0
MAX_CONTRACTS = 50
DD_BUDGET = 2_000.0
PNL_TARGET = 100_000.0


# Baseline params from "Multi-Asset — MNQ/MGC - NEW" preset.
MNQ_BASE_PARAMS: Dict[str, Any] = {
    "ema_len": 11,
    "hma1_len": 13,
    "hma2_len": 21,
    "amp_mult": 2.0,
    "hma_pol_bars": 0,
    "entry_window_bars": 3,
    "ssl_len": 80,
    "ssl_mult": 0.2,
    "hyper_wave_length": 7,
    "signal_type": "SMA",
    "signal_length": 4,
    "mf_length": 31,
    "mf_smooth": 7,
    "hw_dir_on": False,
    "hw_extreme_on": True,
    "hw_extreme": 20.0,
    "sig_extreme_on": True,
    "sig_extreme": 40,
    "hw_range_on": False,
    "hw_range": 10,
    "cloud_on": True,
    "delta_on": True,
    "cloud_zero_on": False,
    "delta_ext_on": False,
    "tick_buffer": 0,
    "max_sl_points": 300.0,
    "cooldown_bars": 3,
    "max_candle_pct": 0.9,
    "signal_candle_sl_on": False,
    "one_trade_per_entry_window": True,
    "hw_partial_pct": 0.0,
    "hw_partial_min_rr": 0.0,
    "block_loss_exit_before_partial": False,
    "final_exit_mode": "HMA rapide/SSL → HW",
    "final_exit_pct": 0.1,
}

MGC_BASE_PARAMS: Dict[str, Any] = {
    "ema_len": 13,
    "hma1_len": 9,
    "hma2_len": 34,
    "amp_mult": 2.0,
    "hma_pol_bars": 3,
    "entry_window_bars": 5,
    "ssl_len": 60,
    "ssl_mult": 0.2,
    "hyper_wave_length": 5,
    "signal_type": "SMA",
    "signal_length": 3,
    "mf_length": 29,
    "mf_smooth": 5,
    "hw_dir_on": True,
    "hw_extreme_on": True,
    "hw_extreme": 20.0,
    "sig_extreme_on": True,
    "sig_extreme": 35,
    "hw_range_on": True,
    "hw_range": 10,
    "cloud_on": True,
    "delta_on": True,
    "cloud_zero_on": False,
    "delta_ext_on": False,
    "tick_buffer": 1,
    "max_sl_points": 100.0,
    "cooldown_bars": 1,
    "max_candle_pct": 0.9,
    "signal_candle_sl_on": False,
    "one_trade_per_entry_window": True,
    "hw_partial_pct": 0.0,
    "hw_partial_min_rr": 0.0,
    "block_loss_exit_before_partial": True,
    "final_exit_mode": "HMA rapide/SSL → HW",
    "final_exit_pct": 0.1,
}

# Baseline risk per the NEW preset.
MNQ_BASE_RISK = 0.0048
MGC_BASE_RISK = 0.0052


def _bw(active: bool, sh: int, sm: int, eh: int, em: int) -> BlackoutWindowSettings:
    return BlackoutWindowSettings(active=active, start_hour=sh, start_minute=sm,
                                  end_hour=eh, end_minute=em)


def base_engine_mnq() -> BacktestEngineSettings:
    """MNQ baseline blackouts from NEW preset: 22-23:59, 11-12, 14-15, 8-9, 12-13."""
    return BacktestEngineSettings(
        auto_close_enabled=True, auto_close_hour=22, auto_close_minute=0,
        blackout_windows=[
            _bw(False, 0, 0, 0, 5),
            _bw(False, 9, 0, 9, 5),
            _bw(False, 12, 0, 14, 0),
            _bw(False, 15, 30, 15, 35),
            _bw(False, 16, 30, 22, 0),
            _bw(True, 22, 0, 23, 59),
            _bw(True, 11, 0, 12, 0),
            _bw(True, 14, 0, 15, 0),
            _bw(True, 8, 0, 9, 0),
            _bw(True, 12, 0, 13, 0),
        ],
        debug=False,
        daily_win_limit_enabled=False, daily_win_limit=500.0,
        daily_loss_limit_enabled=False, daily_loss_limit=700.0,
        daily_limit_mode="after_close",
    )


def base_engine_mgc() -> BacktestEngineSettings:
    """MGC baseline blackouts from NEW preset: 22-23:59, 11-12, 6-7, 7-8, 3-4, 9-10."""
    return BacktestEngineSettings(
        auto_close_enabled=True, auto_close_hour=22, auto_close_minute=0,
        blackout_windows=[
            _bw(False, 0, 0, 0, 5),
            _bw(False, 9, 0, 9, 5),
            _bw(False, 12, 0, 14, 0),
            _bw(False, 15, 30, 15, 35),
            _bw(False, 16, 30, 22, 0),
            _bw(True, 22, 0, 23, 59),
            _bw(True, 3, 0, 4, 0),
            _bw(True, 6, 0, 7, 0),
            _bw(True, 7, 0, 8, 0),
            _bw(True, 9, 0, 10, 0),
            _bw(True, 11, 0, 12, 0),
        ],
        debug=False,
        daily_win_limit_enabled=False, daily_win_limit=500.0,
        daily_loss_limit_enabled=False, daily_loss_limit=700.0,
        daily_limit_mode="after_close",
    )


def _trades_with_source(trades: List[Dict[str, Any]], src: str) -> List[Dict[str, Any]]:
    out = []
    for t in trades:
        if hasattr(t, "model_dump"):
            td = t.model_dump()
        else:
            td = dict(t)
        td["source"] = src
        out.append(td)
    return out


def _combined_dd_dollars(initial_equity: float, trades: List[Dict[str, Any]]) -> Tuple[float, float, float]:
    """Walk merged trades sorted by entry_time and return (net_pnl, max_dd_$, max_dd_%)."""
    active = [t for t in trades if not t.get("excluded", False)]
    sorted_active = sorted(active, key=lambda t: t["entry_time"])
    equity = initial_equity
    peak = initial_equity
    max_dd_dollars = 0.0
    max_dd_pct = 0.0
    for t in sorted_active:
        equity += t["pnl"]
        if equity > peak:
            peak = equity
        dd = peak - equity
        if dd > max_dd_dollars:
            max_dd_dollars = dd
        if peak > 0:
            ddp = dd / peak
            if ddp > max_dd_pct:
                max_dd_pct = ddp
    net = equity - initial_equity
    return net, max_dd_dollars, max_dd_pct * 100.0


def run_multi(
    *,
    mnq_params: Optional[Dict[str, Any]] = None,
    mgc_params: Optional[Dict[str, Any]] = None,
    mnq_engine: Optional[BacktestEngineSettings] = None,
    mgc_engine: Optional[BacktestEngineSettings] = None,
    mnq_risk: float = MNQ_BASE_RISK,
    mgc_risk: float = MGC_BASE_RISK,
    daily_win: Optional[float] = None,
    daily_loss: Optional[float] = None,
    daily_limit_mode: str = "after_close",
    start: str = START,
    end: str = END,
    initial_equity: float = INITIAL_EQUITY,
    max_contracts: int = MAX_CONTRACTS,
    return_trades: bool = False,
) -> Dict[str, Any]:
    """Run MNQ + MGC legs in parallel and combine per backend multi_asset logic."""
    m_params = deepcopy(MNQ_BASE_PARAMS)
    if mnq_params:
        m_params.update(mnq_params)
    g_params = deepcopy(MGC_BASE_PARAMS)
    if mgc_params:
        g_params.update(mgc_params)

    e_mnq = mnq_engine if mnq_engine is not None else base_engine_mnq()
    e_mgc = mgc_engine if mgc_engine is not None else base_engine_mgc()
    if daily_win is not None:
        e_mnq.daily_win_limit_enabled = True
        e_mnq.daily_win_limit = float(daily_win)
    if daily_loss is not None:
        e_mnq.daily_loss_limit_enabled = True
        e_mnq.daily_loss_limit = float(daily_loss)
    e_mnq.daily_limit_mode = daily_limit_mode

    with ThreadPoolExecutor(max_workers=2) as ex:
        f1 = ex.submit(
            run_backtest,
            strategy_name=STRATEGY, symbol="MNQ", interval=INTERVAL,
            start=start, end=end,
            strategy_params=m_params, initial_equity=initial_equity,
            risk_per_trade=mnq_risk, max_contracts=max_contracts,
            engine_settings=e_mnq,
        )
        f2 = ex.submit(
            run_backtest,
            strategy_name=STRATEGY, symbol="MGC", interval=INTERVAL,
            start=start, end=end,
            strategy_params=g_params, initial_equity=initial_equity,
            risk_per_trade=mgc_risk, max_contracts=max_contracts,
            engine_settings=e_mgc,
        )
        r1 = f1.result()
        r2 = f2.result()

    trades1 = _trades_with_source(r1.get("trades", []), "1")
    trades2 = _trades_with_source(r2.get("trades", []), "2")

    merged, _hit = _apply_combined_daily_limits(trades1, trades2, e_mnq)
    net, dd_d, dd_p = _combined_dd_dollars(initial_equity, merged)

    active = [t for t in merged if not t.get("excluded", False)]
    wins = [t for t in active if t["pnl"] > 0]
    losses = [t for t in active if t["pnl"] < 0]
    gross_win = sum(t["pnl"] for t in wins)
    gross_loss = -sum(t["pnl"] for t in losses)
    pf = (gross_win / gross_loss) if gross_loss > 0 else float("inf")
    wr = (len(wins) / len(active) * 100.0) if active else 0.0
    avg_win = (gross_win / len(wins)) if wins else 0.0
    avg_loss = (-gross_loss / len(losses)) if losses else 0.0

    mnq_pnl = sum(t["pnl"] for t in active if t.get("source") == "1")
    mgc_pnl = sum(t["pnl"] for t in active if t.get("source") == "2")

    out = {
        "net_pnl": round(net, 2),
        "max_dd_$": round(dd_d, 2),
        "max_dd_%": round(dd_p, 3),
        "trades": len(active),
        "win_rate": round(wr, 2),
        "profit_factor": round(pf, 3) if pf != float("inf") else None,
        "avg_win": round(avg_win, 2),
        "avg_loss": round(avg_loss, 2),
        "mnq_pnl": round(mnq_pnl, 2),
        "mgc_pnl": round(mgc_pnl, 2),
        "mnq_trades": sum(1 for t in active if t.get("source") == "1"),
        "mgc_trades": sum(1 for t in active if t.get("source") == "2"),
    }
    if return_trades:
        out["trades_list"] = merged
    return out


def fmt(s: Dict[str, Any]) -> str:
    pnl = s["net_pnl"]
    dd = s["max_dd_$"]
    margin = DD_BUDGET - dd
    ratio = pnl / dd if dd > 0 else float("inf")
    pf = s.get("profit_factor")
    return (
        f"PnL=${pnl:>9,.0f} | DD=${dd:>6,.0f} (m=${margin:+7,.0f}) | "
        f"N={s['trades']:>4} (M={s['mnq_trades']:>3}/G={s['mgc_trades']:>3}) | "
        f"WR={s['win_rate']:>5.1f}% | PF={pf} | "
        f"MNQ=${s['mnq_pnl']:>8,.0f}/MGC=${s['mgc_pnl']:>8,.0f} | P/DD={ratio:>5.2f}"
    )


def bench(label: str, **kwargs) -> Dict[str, Any]:
    t0 = time.time()
    s = run_multi(**kwargs)
    s["label"] = label
    s["elapsed_s"] = round(time.time() - t0, 1)
    pass_pnl = "✅" if s["net_pnl"] > PNL_TARGET else " "
    pass_dd = "✅" if s["max_dd_$"] < DD_BUDGET else " "
    print(f"{label:<55s} {fmt(s)}  [{pass_pnl}P{pass_dd}D] ({s['elapsed_s']}s)")
    return s
