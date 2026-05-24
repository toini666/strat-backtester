"""Phase 3 — Filter toggles + extreme thresholds + sig filters.

Anchor: rr_tp=1.25 (Phase 1 winner). Goal: find filter changes that raise
WR further (so we can crank risk for more PnL) OR raise PnL directly.

Tests:
- Each big toggle ON/OFF (hw, sig, cloud, delta, cloud_zero, st, alligator,
  ut, stc, hma, ema, osc) individually.
- `hw_extreme` ∈ {10, 15, 20, 25, 30, 40}  (tighter = stricter)
- `sig_extreme` ∈ {15, 20, 25, 30, 40}
- `hw_level`    ∈ {10, 14, 16, 20, 25}
- `sig_filter_on=True` + `sig_level` ∈ {10, 15, 20, 25}
- `sig_range_reject=True` + `sig_level` ∈ {3, 5, 10, 15}
- `cloud_zero_filter_on=True` + `pts_cloud_zero` ∈ {1, 2}
- `delta_off_mode` ∈ {"both", "counter_trend"}
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


ANCHOR = {"rr_tp": 1.25}
ANCHOR_RISK = SEED_RISK


def _engine():
    es = ui_default_engine_settings(STRATEGY)
    for w in es.blackout_windows:
        w.active = False
    es = make_engine_settings(
        STRATEGY,
        auto_close_hour=SEED_AUTO_CLOSE[0],
        auto_close_minute=SEED_AUTO_CLOSE[1],
        extra_active_windows=[
            {"start_hour": sh, "start_minute": sm, "end_hour": eh, "end_minute": em}
            for sh, sm, eh, em in SEED_BLACKOUTS
        ],
    )
    es.blackout_windows = [w for w in es.blackout_windows if w.active]
    return es


def _bench(label: str, params_override: dict, risk: float = ANCHOR_RISK):
    params = dict(SEED_PARAMS)
    params.update(ANCHOR)
    params.update(params_override)
    r = run_backtest(
        strategy_name=STRATEGY, symbol=SYMBOL, interval=INTERVAL,
        start=START, end=END,
        strategy_params=params,
        initial_equity=INITIAL_EQUITY, risk_per_trade=risk,
        max_contracts=MAX_CONTRACTS, engine_settings=_engine(),
    )
    s = summarize(r)
    flag = " ⭐" if (s["win_rate"] >= GOAL_WR and s["max_dd_$"] <= GOAL_DD) else ""
    print(f"  {label:<52s} {fmt_summary(s)}{flag}")
    return s


def main():
    print(f"=== Phase 3 — Filters + thresholds (anchor: rr_tp=1.25) ===\n")
    print(f"Goal: WR ≥ {GOAL_WR}% / DD ≤ ${GOAL_DD}\n")

    _bench("ANCHOR", {})
    print()

    print("--- 3A: Module on/off toggles ---")
    _bench("osc_off",       {"osc_on": False})
    _bench("ema_off",       {"ema_on": False})
    _bench("st_off",        {"st_on": False})
    _bench("alligator_off", {"alligator_on": False})
    _bench("ut_off",        {"ut_on": False})
    _bench("stc_off",       {"stc_on": False})
    _bench("hma_off",       {"hma_on": False})
    print()

    print("--- 3B: Osc sub-filter toggles ---")
    _bench("hw_filter_off",          {"hw_filter_on": False})
    _bench("hw_extreme_filter_off",  {"hw_extreme_filter_on": False})
    _bench("sig_extreme_filter_off", {"sig_extreme_filter_on": False})
    _bench("cloud_filter_off",       {"cloud_filter_on": False})
    _bench("delta_filter_off",       {"delta_filter_on": False})
    print()

    print("--- 3C: Cloud zero (extra MFI sign filter) ---")
    _bench("cloud_zero ON pts=1",
           {"cloud_zero_filter_on": True, "pts_cloud_zero": 1})
    _bench("cloud_zero ON pts=2",
           {"cloud_zero_filter_on": True, "pts_cloud_zero": 2})
    _bench("cloud_zero ON pts=0 (no score effect)",
           {"cloud_zero_filter_on": True, "pts_cloud_zero": 0})
    print()

    print("--- 3D: Sig bilateral filter (bonus) ---")
    for lvl in [5, 10, 15, 20, 25]:
        _bench(f"sig_filter ON lvl={lvl} pts=1",
               {"sig_filter_on": True, "sig_level": lvl, "pts_sig_value": 1})
    print()

    print("--- 3E: Sig range REJECT (true filter) ---")
    for lvl in [3, 5, 7, 10, 15, 20]:
        _bench(f"sig_range_reject lvl={lvl}",
               {"sig_range_reject": True, "sig_level": lvl})
    print()

    print("--- 3F: hw_extreme threshold (tighter = stricter) ---")
    for hwe in [10, 15, 20, 25, 30, 40, 50, 100]:
        _bench(f"hw_extreme={hwe}", {"hw_extreme": hwe})
    print()

    print("--- 3G: sig_extreme threshold ---")
    for se in [10, 15, 20, 25, 30, 40, 50, 100]:
        _bench(f"sig_extreme={se}", {"sig_extreme": se})
    print()

    print("--- 3H: hw_level ---")
    for hl in [5, 10, 14, 16, 20, 25]:
        _bench(f"hw_level={hl}", {"hw_level": hl})
    print()

    print("--- 3I: delta_off_mode ---")
    _bench("delta_off_mode=both (seed)",  {"delta_off_mode": "both"})
    _bench("delta_off_mode=counter_trend", {"delta_off_mode": "counter_trend"})
    print()


if __name__ == "__main__":
    main()
