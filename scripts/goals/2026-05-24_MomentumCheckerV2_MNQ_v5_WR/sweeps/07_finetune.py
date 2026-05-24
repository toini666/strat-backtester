"""Phase 7 — Fine-tune risk + final combo Pareto.

Top candidates so far (PnL within WR≥50, DD≤$2500):
1. rr=1.5+sr=3 alone, risk=0.625%        → $44,473 / $2,322 / 50.3% (PnL-leader, low WR margin)
2. rr=1.25+sr=3 + BO 14-15+00-01, 0.625% → $41,459 / $2,493 / 56.1%  (WR-leader)
3. rr=1.5+sr=3 + BO 11-12, 0.625%        → $42,374 / $1,971 / 50.4% (DD-leader)
4. rr=1.5+sr=3 + BO 10-11+11-12, 0.625%  → $41,371 / $2,264 / 51.3% (balanced)

Phase 7 plan:
- Fine risk sweep on (1), (3), (4) to find max PnL within $2,500 DD.
- Try adding sl_min_pct / sl_max_points / tick_buffer to top candidates.
- Final shortlist + risk edge crawl at 0.005% granularity.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.goals._shared.harness import run_backtest, summarize, fmt_summary
from scripts.goals._shared.engine_settings import (
    ui_default_engine_settings, make_engine_settings,
)
from sweeps._campaign import (
    SEED_PARAMS, SEED_RISK, SEED_BLACKOUTS, SEED_AUTO_CLOSE,
    START, END, SYMBOL, INTERVAL, STRATEGY, INITIAL_EQUITY, MAX_CONTRACTS,
    GOAL_WR, GOAL_DD,
)


BO_CANDIDATES = {
    "14-15":     (14, 0, 15, 0),
    "11-12":     (11, 0, 12, 0),
    "00-01":     (0,  0, 1,  0),
    "10-11":     (10, 0, 11, 0),
    "01-02":     (1,  0, 2,  0),
    "10-12":     (10, 0, 12, 0),
}


def _engine(extra_blackout_keys: list = None):
    es = ui_default_engine_settings(STRATEGY)
    for w in es.blackout_windows:
        w.active = False
    all_bo = list(SEED_BLACKOUTS)
    for k in (extra_blackout_keys or []):
        all_bo.append(BO_CANDIDATES[k])
    es = make_engine_settings(
        STRATEGY,
        auto_close_hour=SEED_AUTO_CLOSE[0],
        auto_close_minute=SEED_AUTO_CLOSE[1],
        extra_active_windows=[
            {"start_hour": sh, "start_minute": sm, "end_hour": eh, "end_minute": em}
            for sh, sm, eh, em in all_bo
        ],
    )
    es.blackout_windows = [w for w in es.blackout_windows if w.active]
    return es


def _bench(label: str, rr_tp: float, bo_keys: list,
           extra_params: dict = None, risk: float = SEED_RISK):
    params = dict(SEED_PARAMS)
    params["rr_tp"] = rr_tp
    if extra_params:
        params.update(extra_params)
    r = run_backtest(
        strategy_name=STRATEGY, symbol=SYMBOL, interval=INTERVAL,
        start=START, end=END,
        strategy_params=params,
        initial_equity=INITIAL_EQUITY, risk_per_trade=risk,
        max_contracts=MAX_CONTRACTS,
        engine_settings=_engine(bo_keys),
    )
    s = summarize(r)
    flag = " ⭐" if (s["win_rate"] >= GOAL_WR and s["max_dd_$"] <= GOAL_DD) else ""
    print(f"  {label:<70s} {fmt_summary(s)}{flag}")
    return s


def main():
    print(f"=== Phase 7 — Fine-tune + final Pareto ===\n")
    sr3 = {"sig_range_reject": True, "sig_level": 3}

    print("--- 7A: Fine risk sweep on rr=1.5+sr=3 (no extra BO) ---")
    for risk in [0.0060, 0.00625, 0.0064, 0.0066, 0.0068, 0.0070]:
        _bench(f"rr=1.5+sr=3 risk={risk*100:.3f}%",
               rr_tp=1.5, bo_keys=[], extra_params=sr3, risk=risk)
    print()

    print("--- 7B: Fine risk sweep on rr=1.5+sr=3 + BO 11-12 ---")
    for risk in [0.00625, 0.0064, 0.0066, 0.0068, 0.0070, 0.0072, 0.0074]:
        _bench(f"rr=1.5+sr=3 + BO 11-12 risk={risk*100:.3f}%",
               rr_tp=1.5, bo_keys=["11-12"], extra_params=sr3, risk=risk)
    print()

    print("--- 7C: Fine risk sweep on rr=1.5+sr=3 + BO 10-12 ---")
    for risk in [0.00625, 0.0064, 0.0066, 0.0068, 0.0070, 0.0072]:
        _bench(f"rr=1.5+sr=3 + BO 10-12 risk={risk*100:.3f}%",
               rr_tp=1.5, bo_keys=["10-12"], extra_params=sr3, risk=risk)
    print()

    print("--- 7D: Fine risk sweep on rr=1.5+sr=3 + BO 14-15+10-11+00-01 (triple) ---")
    for risk in [0.00625, 0.0068, 0.0070, 0.0072, 0.0075, 0.0080]:
        _bench(f"rr=1.5+sr=3 + BO 14-15+10-11+00-01 risk={risk*100:.3f}%",
               rr_tp=1.5, bo_keys=["14-15", "10-11", "00-01"],
               extra_params=sr3, risk=risk)
    print()

    print("--- 7E: Add SL geometry tweaks (rr=1.5+sr=3, no extra BO) ---")
    base = dict(sr3)
    for label, extra in [
        ("sl_max_points=42 (seed v4)", {"sl_max_points": 42}),
        ("sl_max_points=50",           {"sl_max_points": 50}),
        ("sl_max_points=60",           {"sl_max_points": 60}),
        ("sl_max_points=80",           {"sl_max_points": 80}),
        ("tick_buffer=1",              {"tick_buffer": 1}),
        ("tick_buffer=2",              {"tick_buffer": 2}),
        ("sl_lookback=3",              {"sl_lookback": 3}),
        ("sl_lookback=7",              {"sl_lookback": 7}),
        ("sl_lookback=10",             {"sl_lookback": 10}),
        ("sl_min_pct=0.05",            {"sl_min_pct": 0.05}),
        ("sl_min_pct=0.10",            {"sl_min_pct": 0.10}),
    ]:
        p = dict(base)
        p.update(extra)
        _bench(f"rr=1.5+sr=3 + {label}", rr_tp=1.5, bo_keys=[], extra_params=p)
    print()

    print("--- 7F: pts_alli_offset / pts_sig_extreme / pts_ut_bot=2 on rr=1.5+sr=3 ---")
    for label, extra in [
        ("pts_ut_bot=2",   {"pts_ut_bot": 2}),
        ("pts_alli_off=2", {"pts_alli_offset": 2}),
        ("pts_sig_ext=2",  {"pts_sig_extreme": 2}),
        ("pts_hma_slow=0", {"pts_hma_slow": 0}),
        ("pts_ema_align=3", {"pts_ema_align": 3}),
    ]:
        p = dict(sr3); p.update(extra)
        _bench(f"rr=1.5+sr=3 + {label}", rr_tp=1.5, bo_keys=[], extra_params=p)
    print()


if __name__ == "__main__":
    main()
