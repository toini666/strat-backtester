"""Campaign-local constants for COMBO RIsky Multi-Asset — MGC/MNQ
(MomentumCheckerV2) DD-reduction campaign.

Seed = preset "COMBO RIsky Multi-Asset — MGC/MNQ" (more aggressive variant
of the prior multi-asset combo: MNQ risk=0.60 % with be_at_rr=0 instead of
MNQ risk=0.345 % with be_at_rr=2.0 in the previous winner).

Goal: max_dd_$ < $2,500 with the smallest possible PnL cost.
Budget: 500 sims.

Constraints (locked by user):
- maxContracts = 20 on both legs
- daily limits PREFERABLY OFF. User accepts experiments in "after_close" mode
  out of curiosity, but the deliverable winner should keep them off unless
  they prove necessary.
- auto_close_hour = 22 (CME daily close, ref Brussels)
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.api import BacktestEngineSettings, BlackoutWindowSettings  # noqa: E402
from scripts.goals._shared.harness import run_backtest  # noqa: E402


START = "2025-01-07T00:00"
END = "2026-05-15T22:59"
INITIAL_EQUITY = 50_000.0
STRATEGY = "MomentumCheckerV2"
INTERVAL = "7m"
MAX_CONTRACTS = 20

# ---- BASELINE: COMBO RIsky preset (snapshot from data/presets.json) ----
MGC_PARAMS_BASE: Dict[str, Any] = {
    "long_prep_threshold": 3, "long_threshold": 5,
    "short_prep_threshold": 3, "short_threshold": 5,
    "min_gap": 8, "max_candle_pct": 0.25,
    "sl_lookback": 15, "sl_max_points": 100,
    "rr_tp": 3, "tick_buffer": 2, "be_at_rr": 2,
    "osc_on": True, "hyper_wave_length": 5, "signal_type": "SMA",
    "signal_length": 3, "mf_length": 35, "mf_smooth": 6,
    "hw_filter_on": True, "hw_level": 16,
    "hw_extreme_filter_on": False, "hw_extreme": 15,
    "sig_extreme_filter_on": True, "sig_extreme": 15,
    "cloud_filter_on": True, "delta_filter_on": True,
    "cloud_zero_filter_on": False, "delta_off_mode": "both",
    "pts_hw_sens": 1, "pts_hw_value": 1, "pts_hw_extreme": 1,
    "pts_sig_extreme": 1, "pts_cloud": 1, "pts_delta": 1, "pts_cloud_zero": 0,
    "ema_on": True, "ema_prin_len": 30, "ema_sec_len": 5,
    "pts_ema_break": 1, "pts_ema_align": 1,
    "st_on": True, "st_atr": 10, "st_mult": 3, "pts_st": 1,
    "alligator_on": True, "jaw_length": 13, "teeth_length": 8, "lips_length": 5,
    "jaw_offset": 8, "teeth_offset": 5, "lips_offset": 3,
    "pts_alligator": 1, "pts_alli_offset": 1, "pts_retest_lips": 1,
    "ut_on": False, "ut_key": 1, "ut_atr_period": 10, "pts_ut_bot": 1,
    "stc_on": True, "stc_length": 10, "stc_fast_len": 32, "stc_slow_len": 50,
    "stc_min_long": 1, "stc_max_long": 99, "stc_min_short": 1, "stc_max_short": 99,
    "pts_stc": 1,
    "hma_on": True, "hma_ema_len": 7, "hma1_len": 42, "hma2_len": 84,
    "amp_mult": 2, "hma_pol_bars": 0, "ssl_len": 60, "ssl_mult": 0.2,
    "hma_window_bars": 5, "pts_hma_break": 1, "pts_hma_slow": 1,
}

MNQ_PARAMS_BASE: Dict[str, Any] = {
    "long_prep_threshold": 3, "long_threshold": 5,
    "short_prep_threshold": 3, "short_threshold": 5,
    "min_gap": 10, "max_candle_pct": 0.3,
    "sl_lookback": 5, "sl_max_points": 41,
    "rr_tp": 2.5, "tick_buffer": 2, "be_at_rr": 0,
    "osc_on": True, "hyper_wave_length": 5, "signal_type": "SMA",
    "signal_length": 3, "mf_length": 35, "mf_smooth": 5,
    "hw_filter_on": True, "hw_level": 16,
    "hw_extreme_filter_on": True, "hw_extreme": 20,
    "sig_extreme_filter_on": True, "sig_extreme": 40,
    "cloud_filter_on": True, "delta_filter_on": True,
    "cloud_zero_filter_on": False, "delta_off_mode": "both",
    "pts_hw_sens": 1, "pts_hw_value": 1, "pts_hw_extreme": 1,
    "pts_sig_extreme": 1, "pts_cloud": 1, "pts_delta": 1, "pts_cloud_zero": 0,
    "ema_on": True, "ema_prin_len": 30, "ema_sec_len": 20,
    "pts_ema_break": 1, "pts_ema_align": 2,
    "st_on": True, "st_atr": 10, "st_mult": 3, "pts_st": 1,
    "alligator_on": True, "jaw_length": 13, "teeth_length": 8, "lips_length": 5,
    "jaw_offset": 8, "teeth_offset": 5, "lips_offset": 3,
    "pts_alligator": 1, "pts_alli_offset": 1, "pts_retest_lips": 1,
    "ut_on": True, "ut_key": 1, "ut_atr_period": 10, "pts_ut_bot": 1,
    "stc_on": True, "stc_length": 12, "stc_fast_len": 26, "stc_slow_len": 50,
    "stc_min_long": 1, "stc_max_long": 99, "stc_min_short": 1, "stc_max_short": 99,
    "pts_stc": 1,
    "hma_on": True, "hma_ema_len": 7, "hma1_len": 42, "hma2_len": 84,
    "amp_mult": 3.5, "hma_pol_bars": 0, "ssl_len": 60, "ssl_mult": 0.2,
    "hma_window_bars": 5, "pts_hma_break": 1, "pts_hma_slow": 1,
}

MGC_RISK_BASE = 0.0053  # 0.53 %
MNQ_RISK_BASE = 0.0060  # 0.60 %

# Baseline blackouts (per preset)
MGC_BLACKOUTS_BASE: List[Tuple[int, int, int, int]] = [
    (12, 30, 14, 0),
    (15, 30, 17, 0),
    (18, 0, 19, 0),
    (20, 0, 21, 0),
    (22, 0, 23, 59),
]
MNQ_BLACKOUTS_BASE: List[Tuple[int, int, int, int]] = [
    (9, 0, 10, 0),
    (13, 0, 14, 30),
    (17, 0, 23, 59),  # the preset has a duplicate 22-24 window — same effect
    (22, 0, 23, 59),
]


def _mk_engine(
    blackouts: List[Tuple[int, int, int, int]],
    *,
    daily_win_limit_enabled: bool = False,
    daily_win_limit: float = 500.0,
    daily_loss_limit_enabled: bool = False,
    daily_loss_limit: float = 700.0,
    daily_limit_mode: str = "after_close",
) -> BacktestEngineSettings:
    return BacktestEngineSettings(
        auto_close_enabled=True,
        auto_close_hour=22,
        auto_close_minute=0,
        blackout_windows=[
            BlackoutWindowSettings(
                active=True,
                start_hour=h1, start_minute=m1,
                end_hour=h2, end_minute=m2,
            )
            for (h1, m1, h2, m2) in blackouts
        ],
        debug=False,
        daily_win_limit_enabled=daily_win_limit_enabled,
        daily_win_limit=daily_win_limit,
        daily_loss_limit_enabled=daily_loss_limit_enabled,
        daily_loss_limit=daily_loss_limit,
        daily_limit_mode=daily_limit_mode,
    )


def run_leg(
    symbol: str,
    params: Dict[str, Any],
    risk: float,
    blackouts: List[Tuple[int, int, int, int]],
    *,
    engine_overrides: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    if engine_overrides is None:
        engine_overrides = {}
    return run_backtest(
        strategy_name=STRATEGY,
        symbol=symbol,
        interval=INTERVAL,
        start=START,
        end=END,
        strategy_params=params,
        initial_equity=INITIAL_EQUITY,
        risk_per_trade=risk,
        max_contracts=MAX_CONTRACTS,
        engine_settings=_mk_engine(blackouts, **engine_overrides),
    )


def _combined_metrics(initial_equity: float, trades: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Mirrors backend `_compute_combined_metrics` + tracks max_drawdown_dollars."""
    active = [t for t in trades if not t.get("excluded", False)]
    sorted_active = sorted(active, key=lambda t: t["entry_time"])

    equity = initial_equity
    peak = initial_equity
    max_dd_pct = 0.0
    max_dd_dollars = 0.0
    dd_trough_time = None
    dd_peak_time = None
    cur_peak_time = None
    for trade in sorted_active:
        equity += trade["pnl"]
        if equity > peak:
            peak = equity
            cur_peak_time = trade["entry_time"]
        dollar_dd = peak - equity
        pct_dd = dollar_dd / peak if peak > 0 else 0.0
        if pct_dd > max_dd_pct:
            max_dd_pct = pct_dd
        if dollar_dd > max_dd_dollars:
            max_dd_dollars = dollar_dd
            dd_trough_time = trade["entry_time"]
            dd_peak_time = cur_peak_time

    total_pnl = equity - initial_equity
    total = len(active)
    wins = [t for t in active if t["pnl"] > 0]
    losses = [t for t in active if t["pnl"] < 0]
    win_rate = (len(wins) / total * 100) if total > 0 else 0.0
    gross_win = sum(t["pnl"] for t in wins)
    gross_loss = -sum(t["pnl"] for t in losses)
    pf = (gross_win / gross_loss) if gross_loss > 0 else float("inf")

    return {
        "net_pnl": round(total_pnl, 2),
        "trades": total,
        "win_rate": round(win_rate, 1),
        "max_dd_$": round(max_dd_dollars, 2),
        "max_dd_%": round(max_dd_pct * 100, 2),
        "profit_factor": round(pf, 2) if pf != float("inf") else None,
        "dd_peak_time": dd_peak_time,
        "dd_trough_time": dd_trough_time,
    }


def run_multi(
    *,
    mgc_params: Optional[Dict[str, Any]] = None,
    mgc_risk: float = MGC_RISK_BASE,
    mgc_blackouts: Optional[List[Tuple[int, int, int, int]]] = None,
    mnq_params: Optional[Dict[str, Any]] = None,
    mnq_risk: float = MNQ_RISK_BASE,
    mnq_blackouts: Optional[List[Tuple[int, int, int, int]]] = None,
    engine_overrides_mgc: Optional[Dict[str, Any]] = None,
    engine_overrides_mnq: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    if mgc_params is None:
        mgc_params = MGC_PARAMS_BASE
    if mnq_params is None:
        mnq_params = MNQ_PARAMS_BASE
    r_mgc = run_leg("MGC", mgc_params, mgc_risk,
                    mgc_blackouts or MGC_BLACKOUTS_BASE,
                    engine_overrides=engine_overrides_mgc)
    r_mnq = run_leg("MNQ", mnq_params, mnq_risk,
                    mnq_blackouts or MNQ_BLACKOUTS_BASE,
                    engine_overrides=engine_overrides_mnq)

    t_mgc = r_mgc.get("trades", [])
    t_mnq = r_mnq.get("trades", [])
    for t in t_mgc:
        t["_leg"] = "MGC"
    for t in t_mnq:
        t["_leg"] = "MNQ"

    merged = t_mgc + t_mnq
    summary = _combined_metrics(INITIAL_EQUITY, merged)

    def _leg_summary(trades):
        active = [t for t in trades if not t.get("excluded", False)]
        return {
            "trades": len(active),
            "pnl": round(sum(t["pnl"] for t in active), 2),
        }

    summary["mgc"] = _leg_summary(t_mgc)
    summary["mnq"] = _leg_summary(t_mnq)
    summary["_merged"] = merged
    return summary


def fmt_multi(s: Dict[str, Any]) -> str:
    return (
        f"PnL=${s['net_pnl']:>9,.0f} | DD=${s['max_dd_$']:>6,.0f} | "
        f"N={s['trades']:>4} | WR={s['win_rate']:>4.1f}% | PF={s['profit_factor']} | "
        f"MGC=${s['mgc']['pnl']:>7,.0f}({s['mgc']['trades']}) "
        f"MNQ=${s['mnq']['pnl']:>7,.0f}({s['mnq']['trades']})"
    )
