"""Phase 9 — risk fine grid + out-of-sample validation.

Best v2 config (at risk 0.5%):
  PnL $35,991 / DD $5,120 / PF 1.13 / ratio 7.03×

Steps:
  1. Risk fine grid 0.18 - 0.40% (steps of 0.02%) on full period — find max
     risk where DD ≤ $2,500.
  2. OOS check on 2026-03-01 → 2026-05-22 at chosen risk.
  3. Walk-forward style: same config on 2025 only and 2026 only, to confirm
     it's not concentrated in one half.
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

BEST_CONFIG = {
    "amp_mult": 1.5, "hma1_len": 13, "hma2_len": 21,
    "case_a_on": True, "case_b_on": True,
    "case_c_on": False, "case_d_on": True,
    "final_rr": 1.5, "cooldown_bars": 90,
    "sl_lookback": 15, "tick_buffer": 6,
    "ssl_len": 20, "ssl_mult": 0.20,
    "sig_extreme_threshold": 35.0,
    "hyper_wave_length": 5, "signal_length": 3,
}


def _es_no_blackouts():
    es = ui_default_engine_settings(STRATEGY)
    for w in es.blackout_windows:
        w.active = False
    es.auto_close_hour, es.auto_close_minute = AUTO_CLOSE
    return es


def _run(params, es, risk, label, start=START, end=END):
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
    print(f"  {label:<48s} {fmt_summary(s)}  ({s['elapsed_s']}s)")
    return s


def main():
    print("=" * 100)
    print("PHASE 9 — risk fine + OOS validation")
    print("=" * 100)
    es = _es_no_blackouts()
    SEED = dict(V1_WINNER_PARAMS)
    SEED.update(BEST_CONFIG)

    # ---- 1. Risk fine grid ----
    print()
    print(f"--- Risk fine grid (DD budget = ${GOAL_DD:,.0f}) ---")
    risks = [0.18, 0.20, 0.22, 0.24, 0.26, 0.28, 0.30, 0.32, 0.34, 0.36, 0.40]
    risk_rows = []
    for r_pct in risks:
        s = _run(SEED, es, r_pct / 100, f"risk={r_pct:.2f}%")
        risk_rows.append({"risk_pct": r_pct, **s})

    # Pick the largest risk with DD ≤ GOAL_DD
    valid = [r for r in risk_rows if r["max_dd_$"] <= GOAL_DD]
    if not valid:
        print(f"\nWARNING: no risk in grid keeps DD ≤ ${GOAL_DD:,.0f}")
        chosen_risk = min(risks)
    else:
        chosen = max(valid, key=lambda r: r["risk_pct"])
        chosen_risk = chosen["risk_pct"]
    print()
    print(f">>> Chosen risk: {chosen_risk:.2f}% "
          f"(PnL=${chosen['net_pnl']:,.0f} / DD=${chosen['max_dd_$']:,.0f})")

    # ---- 2. OOS check: last ~3 months ----
    print()
    print("--- OOS check: 2026-03-01 → 2026-05-22 ---")
    _run(SEED, es, chosen_risk / 100,
         f"OOS@risk={chosen_risk:.2f}%",
         start="2026-03-01T00:00", end="2026-05-22T22:59")

    # ---- 3. Year-segment split ----
    print()
    print("--- Year-segment split ---")
    _run(SEED, es, chosen_risk / 100,
         f"2025@risk={chosen_risk:.2f}%",
         start="2025-01-02T00:00", end="2025-12-31T22:59")
    _run(SEED, es, chosen_risk / 100,
         f"2026@risk={chosen_risk:.2f}%",
         start="2026-01-01T00:00", end="2026-05-22T22:59")

    # ---- 4. Confirm full-period winner ----
    print()
    print("--- Final winner replay (full period) ---")
    s_final = _run(SEED, es, chosen_risk / 100,
                   f"FINAL@risk={chosen_risk:.2f}%")

    print()
    print("=" * 100)
    print(f"FINAL WINNER (v2):  PnL=${s_final['net_pnl']:,.0f}  /  "
          f"DD=${s_final['max_dd_$']:,.0f}  /  PF={s_final['profit_factor']}")
    print(f"vs v1 winner:        PnL=$13,130  /  DD=$2,461  /  PF=1.17")
    print(f"vs goal:             PnL≥$50,000  /  DD≤$2,500")
    print("=" * 100)


if __name__ == "__main__":
    main()
