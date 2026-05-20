"""Campaign-local constants and multi-asset harness for MomentumCheckerV2 multi-asset
(MGC + MNQ 7m) DD-reduction campaign.

Goal: reduce combined max_dd_$ below $2,300 (ideally below $2,000) while
sacrificing as little PnL as possible. Budget: 500 sims.

Constraints (locked):
- maxContracts = 20 on both legs
- daily_win_limit / daily_loss_limit OFF on both legs
- auto_close_hour = 22 (CME daily close, ref Brussels)

Reference: scripts/goals/2026-05-20_MomentumCheckerV2_MNQ_v2/REPORT.md and
scripts/goals/2026-05-20_MomentumCheckerV2_MGC/REPORT.md.
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

# ---- BASELINE PRESET (from "Base combo momCheckv2 Multi-Asset — MGC/MNQ") ----
# These are the mono-asset winners glued together.

MGC_PARAMS_BASE: Dict[str, Any] = {
    "long_prep_threshold": 3, "long_threshold": 5,
    "short_prep_threshold": 3, "short_threshold": 5,
    "min_gap": 8, "max_candle_pct": 0.3,
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
    "amp_mult": 2, "hma_pol_bars": -1, "ssl_len": 60, "ssl_mult": 0.2,
    "hma_window_bars": 5, "pts_hma_break": 1, "pts_hma_slow": 1,
}

MNQ_PARAMS_BASE: Dict[str, Any] = {
    "long_prep_threshold": 3, "long_threshold": 5,
    "short_prep_threshold": 3, "short_threshold": 5,
    "min_gap": 9, "max_candle_pct": 0.3,
    "sl_lookback": 5, "sl_max_points": 60,
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
    "pts_ema_break": 1, "pts_ema_align": 1,
    "st_on": True, "st_atr": 10, "st_mult": 3, "pts_st": 1,
    "alligator_on": True, "jaw_length": 13, "teeth_length": 8, "lips_length": 5,
    "jaw_offset": 8, "teeth_offset": 5, "lips_offset": 3,
    "pts_alligator": 1, "pts_alli_offset": 1, "pts_retest_lips": 1,
    "ut_on": True, "ut_key": 1, "ut_atr_period": 10, "pts_ut_bot": 1,
    "stc_on": True, "stc_length": 12, "stc_fast_len": 26, "stc_slow_len": 50,
    "stc_min_long": 1, "stc_max_long": 99, "stc_min_short": 1, "stc_max_short": 99,
    "pts_stc": 1,
    "hma_on": True, "hma_ema_len": 7, "hma1_len": 42, "hma2_len": 84,
    "amp_mult": 3.5, "hma_pol_bars": -1, "ssl_len": 60, "ssl_mult": 0.2,
    "hma_window_bars": 5, "pts_hma_break": 1, "pts_hma_slow": 1,
}


def _mk_engine(blackouts: List[Tuple[int, int, int, int]]) -> BacktestEngineSettings:
    """Build engine settings with auto-close 22:00 + given active blackout windows
    [(start_h, start_m, end_h, end_m), ...]. Daily limits off (campaign constraint)."""
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
        daily_win_limit_enabled=False,
        daily_win_limit=500,
        daily_loss_limit_enabled=False,
        daily_loss_limit=700,
        daily_limit_mode="after_close",
    )


# Baseline blackouts (from the preset)
MGC_BLACKOUTS_BASE = [
    (12, 30, 14, 0),
    (18, 0, 19, 0),
    (20, 0, 21, 0),
    (22, 0, 23, 59),
]
MNQ_BLACKOUTS_BASE = [
    (9, 0, 10, 0),
    (13, 0, 14, 30),
    (17, 0, 23, 59),  # the preset has 17-24 + a duplicate 22-24 — same effect
    (22, 0, 23, 59),
]


def run_leg(
    symbol: str,
    params: Dict[str, Any],
    risk: float,
    blackouts: List[Tuple[int, int, int, int]],
) -> Dict[str, Any]:
    """Run one leg and return the simulator result dict."""
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
        engine_settings=_mk_engine(blackouts),
    )


def _combined_metrics(initial_equity: float, trades: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Mirrors backend `_compute_combined_metrics` + adds max_drawdown_dollars.

    Sorts active trades by entry_time, accumulates pnl, tracks the worst
    peak-to-trough in $ AND %.
    """
    active = [t for t in trades if not t.get("excluded", False)]
    sorted_active = sorted(active, key=lambda t: t["entry_time"])

    equity = initial_equity
    peak = initial_equity
    max_dd_pct = 0.0
    max_dd_dollars = 0.0
    for trade in sorted_active:
        equity += trade["pnl"]
        if equity > peak:
            peak = equity
        dollar_dd = peak - equity
        pct_dd = dollar_dd / peak if peak > 0 else 0.0
        if pct_dd > max_dd_pct:
            max_dd_pct = pct_dd
        if dollar_dd > max_dd_dollars:
            max_dd_dollars = dollar_dd

    total_pnl = equity - initial_equity
    total = len(active)
    wins = [t for t in active if t["pnl"] > 0]
    losses = [t for t in active if t["pnl"] < 0]
    win_rate = (len(wins) / total * 100) if total > 0 else 0.0
    gross_win = sum(t["pnl"] for t in wins)
    gross_loss = -sum(t["pnl"] for t in losses)
    pf = (gross_win / gross_loss) if gross_loss > 0 else float("inf")
    avg_win = (gross_win / len(wins)) if wins else 0.0
    avg_loss = -(gross_loss / len(losses)) if losses else 0.0

    return {
        "net_pnl": round(total_pnl, 2),
        "trades": total,
        "win_rate": round(win_rate, 1),
        "max_dd_$": round(max_dd_dollars, 2),
        "max_dd_%": round(max_dd_pct * 100, 2),
        "profit_factor": round(pf, 2) if pf != float("inf") else None,
        "avg_win": round(avg_win, 2),
        "avg_loss": round(avg_loss, 2),
    }


def run_multi(
    *,
    mgc_params: Dict[str, Any],
    mgc_risk: float,
    mgc_blackouts: Optional[List[Tuple[int, int, int, int]]] = None,
    mnq_params: Dict[str, Any],
    mnq_risk: float,
    mnq_blackouts: Optional[List[Tuple[int, int, int, int]]] = None,
) -> Dict[str, Any]:
    """Run both legs and return combined summary + per-leg detail."""
    r_mgc = run_leg("MGC", mgc_params, mgc_risk, mgc_blackouts or MGC_BLACKOUTS_BASE)
    r_mnq = run_leg("MNQ", mnq_params, mnq_risk, mnq_blackouts or MNQ_BLACKOUTS_BASE)

    t_mgc = r_mgc.get("trades", [])
    t_mnq = r_mnq.get("trades", [])
    for t in t_mgc:
        t["_leg"] = "MGC"
    for t in t_mnq:
        t["_leg"] = "MNQ"

    merged = t_mgc + t_mnq
    summary = _combined_metrics(INITIAL_EQUITY, merged)

    # Per-leg active PnL
    def _leg_summary(trades):
        active = [t for t in trades if not t.get("excluded", False)]
        return {
            "trades": len(active),
            "pnl": round(sum(t["pnl"] for t in active), 2),
        }

    summary["mgc"] = _leg_summary(t_mgc)
    summary["mnq"] = _leg_summary(t_mnq)
    summary["_merged"] = merged  # for hour-bucket analysis
    return summary


def fmt_multi(s: Dict[str, Any]) -> str:
    return (
        f"PnL=${s['net_pnl']:>9,.0f} | DD=${s['max_dd_$']:>6,.0f} | "
        f"N={s['trades']:>4} | WR={s['win_rate']:>4.1f}% | PF={s['profit_factor']} | "
        f"MGC=${s['mgc']['pnl']:>7,.0f}({s['mgc']['trades']}) "
        f"MNQ=${s['mnq']['pnl']:>7,.0f}({s['mnq']['trades']})"
    )
