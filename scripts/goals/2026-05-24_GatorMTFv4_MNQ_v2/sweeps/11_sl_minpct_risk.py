"""Phase 11 — sl_min_pct × risk grid to break the 1-contract DD floor.

Phase 10 forensics found:
  - DD = $2,126 is a 165-trade slow grind (2025-11-13 → 2025-12-19), not a single event.
  - Most positions are 1 contract because sl_min_pct=0.15% pins SL distance to
    50 points (~$100 risk per contract), which exceeds 0.28% risk budget ($140).
  - At risk 0.30%+, 2-contract trades emerge and DD scales up.

Test:
  (A) reduce sl_min_pct so tighter SLs allow 2-contract sizing at the same risk
      → PnL up, DD up — ratio?
  (B) increase risk to force 2-contract for most → PnL/DD ratio at higher equity allocation
  (C) one_trade_per_window=False spot-check
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
)

WINNER = {
    "amp_mult": 1.5, "hma1_len": 13, "hma2_len": 21,
    "case_a_on": True, "case_b_on": True,
    "case_c_on": False, "case_d_on": True,
    "final_rr": 1.5, "cooldown_bars": 90,
    "sl_lookback": 15, "tick_buffer": 6,
    "ssl_len": 20, "ssl_mult": 0.20,
    "sig_extreme_threshold": 33.0,
}


def _es_no_blackouts():
    es = ui_default_engine_settings(STRATEGY)
    for w in es.blackout_windows:
        w.active = False
    es.auto_close_hour, es.auto_close_minute = AUTO_CLOSE
    return es


def _run(params, risk, es, label):
    t0 = time.time()
    r = run_backtest(
        strategy_name=STRATEGY,
        symbol=SYMBOL, interval=INTERVAL,
        start=START, end=END,
        strategy_params=params,
        initial_equity=INITIAL_EQUITY,
        risk_per_trade=risk,
        max_contracts=MAX_CONTRACTS,
        engine_settings=es,
    )
    s = summarize(r)
    s["elapsed_s"] = round(time.time() - t0, 1)
    print(f"  {label:<40s} {fmt_summary(s)}  ({s['elapsed_s']}s)")
    return s


def main():
    print("=" * 100)
    print("PHASE 11 — sl_min_pct × risk grid to break the 1-contract DD floor")
    print("=" * 100)
    es = _es_no_blackouts()
    SEED = dict(V1_WINNER_PARAMS)
    SEED.update(WINNER)

    # ---- (A) sl_min_pct × risk grid ----
    print()
    print("--- (A) sl_min_pct × risk grid ---")
    rows = []
    for sl_pct in [0.05, 0.08, 0.10, 0.12, 0.15, 0.18]:
        for risk_pct in [0.20, 0.28, 0.40, 0.60, 0.80]:
            p = dict(SEED)
            p["sl_min_pct"] = sl_pct
            s = _run(p, risk_pct / 100, es, f"sl_min_pct={sl_pct:.2f} risk={risk_pct:.2f}%")
            rows.append({"sl_min_pct": sl_pct, "risk_pct": risk_pct, **s})

    print()
    print("--- (B) one_trade_per_window=False spot-check ---")
    p = dict(SEED)
    p["one_trade_per_window"] = False
    _run(p, 0.28 / 100, es, "otpw=False risk=0.28%")
    _run(p, 0.18 / 100, es, "otpw=False risk=0.18%")

    print()
    print("=" * 100)
    print("(A) Top 10 by PnL/DD ratio (DD ≤ $2,500):")
    print("=" * 100)
    valid = [r for r in rows if r["max_dd_$"] > 0 and r["max_dd_$"] <= 2500]
    valid.sort(key=lambda x: x["net_pnl"] / x["max_dd_$"], reverse=True)
    if valid:
        for r in valid[:10]:
            ratio = r["net_pnl"] / r["max_dd_$"]
            print(f"  sl_min_pct={r['sl_min_pct']:.2f} risk={r['risk_pct']:.2f}%  "
                  f"PnL=${r['net_pnl']:>8,.0f}  DD=${r['max_dd_$']:>6,.0f}  "
                  f"ratio={ratio:.2f}×  PF={r['profit_factor']}")
    else:
        print("  (none meet DD ≤ $2,500 — the budget floor is structural)")

    print()
    print("Top 10 raw PnL (any DD):")
    by_pnl = sorted(rows, key=lambda x: x["net_pnl"], reverse=True)
    for r in by_pnl[:10]:
        ratio = r["net_pnl"] / r["max_dd_$"] if r["max_dd_$"] > 0 else 0
        print(f"  sl_min_pct={r['sl_min_pct']:.2f} risk={r['risk_pct']:.2f}%  "
              f"PnL=${r['net_pnl']:>8,.0f}  DD=${r['max_dd_$']:>6,.0f}  "
              f"ratio={ratio:.2f}×  PF={r['profit_factor']}")


if __name__ == "__main__":
    main()
