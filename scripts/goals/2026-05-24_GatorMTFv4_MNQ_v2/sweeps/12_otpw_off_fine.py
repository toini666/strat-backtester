"""Phase 12 — one_trade_per_window=False fine risk grid.

Phase 11 spot-check found otpw=False at risk=0.28% → $17,576 / $2,455 (+$799 vs otpw=True).
Find max risk under DD ≤ $2,500 with otpw=False. Also confirm otpw=False holds OOS.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.goals._shared.harness import run_backtest, summarize, fmt_summary
from scripts.goals._shared.engine_settings import ui_default_engine_settings
from sweeps._campaign import (
    V1_WINNER_PARAMS, AUTO_CLOSE,
    START, END, SYMBOL, INTERVAL, STRATEGY,
    INITIAL_EQUITY, MAX_CONTRACTS,
    GOAL_DD,
)

WINNER = {
    "amp_mult": 1.5, "hma1_len": 13, "hma2_len": 21,
    "case_a_on": True, "case_b_on": True,
    "case_c_on": False, "case_d_on": True,
    "final_rr": 1.5, "cooldown_bars": 90,
    "sl_lookback": 15, "tick_buffer": 6,
    "ssl_len": 20, "ssl_mult": 0.20,
    "sig_extreme_threshold": 33.0,
    "one_trade_per_window": False,  # NEW
}


def _es_no_blackouts():
    es = ui_default_engine_settings(STRATEGY)
    for w in es.blackout_windows:
        w.active = False
    es.auto_close_hour, es.auto_close_minute = AUTO_CLOSE
    return es


def _run(params, risk, es, label, start=START, end=END):
    t0 = time.time()
    r = run_backtest(
        strategy_name=STRATEGY,
        symbol=SYMBOL, interval=INTERVAL,
        start=start, end=end,
        strategy_params=params,
        initial_equity=INITIAL_EQUITY,
        risk_per_trade=risk,
        max_contracts=MAX_CONTRACTS,
        engine_settings=es,
    )
    s = summarize(r)
    s["elapsed_s"] = round(time.time() - t0, 1)
    print(f"  {label:<45s} {fmt_summary(s)}  ({s['elapsed_s']}s)")
    return s


def main():
    print("=" * 100)
    print("PHASE 12 — otpw=False fine risk grid + OOS")
    print("=" * 100)
    es = _es_no_blackouts()
    SEED = dict(V1_WINNER_PARAMS)
    SEED.update(WINNER)

    print()
    print("--- Risk fine grid (otpw=False) ---")
    rows = []
    for risk_pct in [0.18, 0.20, 0.22, 0.24, 0.26, 0.28, 0.30, 0.32, 0.34]:
        s = _run(SEED, risk_pct / 100, es, f"risk={risk_pct:.2f}%")
        rows.append({"risk_pct": risk_pct, **s})

    # pick max risk under DD budget
    valid = [r for r in rows if r["max_dd_$"] <= GOAL_DD]
    if valid:
        chosen = max(valid, key=lambda r: r["risk_pct"])
        chosen_r = chosen["risk_pct"]
        print(f"\n>>> Max risk under DD={GOAL_DD}: {chosen_r:.2f}% "
              f"(PnL=${chosen['net_pnl']:,.0f} / DD=${chosen['max_dd_$']:,.0f})")
    else:
        chosen_r = 0.18

    # OOS validation
    print()
    print("--- OOS validation (otpw=False) ---")
    _run(SEED, chosen_r / 100, es, f"OOS@risk={chosen_r:.2f}%",
         start="2026-03-01T00:00", end="2026-05-22T22:59")
    _run(SEED, chosen_r / 100, es, f"2025@risk={chosen_r:.2f}%",
         start="2025-01-02T00:00", end="2025-12-31T22:59")
    _run(SEED, chosen_r / 100, es, f"2026@risk={chosen_r:.2f}%",
         start="2026-01-01T00:00", end="2026-05-22T22:59")


if __name__ == "__main__":
    main()
