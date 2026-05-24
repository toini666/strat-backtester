"""Phase 0 — replay v1 winner + measure "no blackouts at 0.5 %" baseline.

Two anchors:
  (a) v1 winner exact replay (risk 0.26 %, full 10-window blackout schedule).
      Expected: PnL ≈ $13,130 / DD ≈ $2,461.
  (b) "Clean sweep seed" — v1 winner params, NO blackouts, risk = 0.5 %.
      Used as the starting baseline for structural Phase 1-6 sweeps.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.goals._shared.harness import run_backtest, summarize, fmt_summary
from scripts.goals._shared.engine_settings import ui_default_engine_settings
from sweeps._campaign import (
    V1_WINNER_PARAMS, V1_WINNER_RISK, V1_WINNER_BLACKOUTS,
    SWEEP_RISK, AUTO_CLOSE,
    START, END, SYMBOL, INTERVAL, STRATEGY,
    INITIAL_EQUITY, MAX_CONTRACTS,
)


def _es_with_blackouts(blackouts):
    es = ui_default_engine_settings(STRATEGY)
    target = {(sh, sm, eh, em) for sh, sm, eh, em in blackouts}
    for w in es.blackout_windows:
        w.active = (w.start_hour, w.start_minute, w.end_hour, w.end_minute) in target
    # Insert any missing target windows.
    have = {(w.start_hour, w.start_minute, w.end_hour, w.end_minute) for w in es.blackout_windows}
    from backend.api import BlackoutWindow
    for sh, sm, eh, em in blackouts:
        if (sh, sm, eh, em) not in have:
            es.blackout_windows.append(
                BlackoutWindow(active=True, start_hour=sh, start_minute=sm,
                               end_hour=eh, end_minute=em)
            )
    es.auto_close_hour, es.auto_close_minute = AUTO_CLOSE
    return es


def main():
    print("=" * 90)
    print("PHASE 0 — v1 winner replay + clean sweep seed baseline")
    print("=" * 90)

    # --- (a) v1 winner exact replay ----------------------------------------
    print()
    print("(a) v1 winner exact replay")
    print(f"    risk={V1_WINNER_RISK*100:.2f}%  blackouts={len(V1_WINNER_BLACKOUTS)} windows")
    es_a = _es_with_blackouts(V1_WINNER_BLACKOUTS)
    r_a = run_backtest(
        strategy_name=STRATEGY,
        symbol=SYMBOL, interval=INTERVAL,
        start=START, end=END,
        strategy_params=V1_WINNER_PARAMS,
        initial_equity=INITIAL_EQUITY,
        risk_per_trade=V1_WINNER_RISK,
        max_contracts=MAX_CONTRACTS,
        engine_settings=es_a,
    )
    s_a = summarize(r_a)
    print("    " + fmt_summary(s_a))
    print(f"    expected PnL ≈ $13,130 / DD ≈ $2,461 / N ≈ 1,439")

    pnl_diff = s_a["net_pnl"] - 13130.0
    dd_diff = s_a["max_dd_$"] - 2461.0
    ok = abs(pnl_diff) < 200.0 and abs(dd_diff) < 200.0
    print(f"    diff: PnL={pnl_diff:+,.0f}  DD={dd_diff:+,.0f}  → {'MATCH' if ok else 'MISMATCH'}")
    if not ok:
        print("\nv1 winner replay does not match within tolerance — investigate.")
        sys.exit(1)

    # --- (b) clean sweep seed: v1 winner params, no blackouts, risk 0.5 % --
    print()
    print("(b) clean sweep seed (v1 winner params, NO blackouts, risk 0.5 %)")
    es_b = _es_with_blackouts([])
    r_b = run_backtest(
        strategy_name=STRATEGY,
        symbol=SYMBOL, interval=INTERVAL,
        start=START, end=END,
        strategy_params=V1_WINNER_PARAMS,
        initial_equity=INITIAL_EQUITY,
        risk_per_trade=SWEEP_RISK,
        max_contracts=MAX_CONTRACTS,
        engine_settings=es_b,
    )
    s_b = summarize(r_b)
    print("    " + fmt_summary(s_b))
    print()
    print("→ Use this baseline (b) as the reference point for Phase 1-6 sweeps.")
    print("  Phase 7 re-introduces blackouts on the new best config.")


if __name__ == "__main__":
    main()
