"""Phase 9B — OOS robustness comparison of top candidates.

The sharp ssl_mult=0.20 peak is suspicious — neighbors are much worse.
Compare to more robust alternatives that have similar IS performance:
  - A: smult=0.20 thr=35 (sharp peak, ratio 7.03×) ← current winner
  - B: smult=0.20 thr=33 (very close, ratio 7.01×)
  - C: smult=0.17 thr=35 (off-peak smult, similar thr)
  - D: ssl_len=15 ssl_mult=0.20 thr=35 (off-peak slen)
  - E: ssl_len=60 ssl_mult=0.20 thr=35 (back to original ssl_len)

Pick the candidate with the most consistent split between 2025 and 2026.
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

BASE = {
    "amp_mult": 1.5, "hma1_len": 13, "hma2_len": 21,
    "case_a_on": True, "case_b_on": True,
    "case_c_on": False, "case_d_on": True,
    "final_rr": 1.5, "cooldown_bars": 90,
    "sl_lookback": 15, "tick_buffer": 6,
    "hyper_wave_length": 5, "signal_length": 3,
}

CANDIDATES = {
    "A": {"ssl_len": 20, "ssl_mult": 0.20, "sig_extreme_threshold": 35.0},
    "B": {"ssl_len": 20, "ssl_mult": 0.20, "sig_extreme_threshold": 33.0},
    "C": {"ssl_len": 20, "ssl_mult": 0.17, "sig_extreme_threshold": 35.0},
    "D": {"ssl_len": 15, "ssl_mult": 0.20, "sig_extreme_threshold": 35.0},
    "E": {"ssl_len": 60, "ssl_mult": 0.20, "sig_extreme_threshold": 35.0},
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
    print(f"  {label:<50s} {fmt_summary(s)}  ({s['elapsed_s']}s)")
    return s


def find_max_risk_under_dd(params, es, dd_budget=2500.0):
    risks = [0.18, 0.20, 0.22, 0.24, 0.26, 0.28, 0.30, 0.32]
    chosen = None
    chosen_pnl = -1e18
    for r in risks:
        res = run_backtest(
            strategy_name=STRATEGY,
            symbol=SYMBOL, interval=INTERVAL,
            start=START, end=END,
            strategy_params=params,
            initial_equity=INITIAL_EQUITY,
            risk_per_trade=r / 100,
            max_contracts=MAX_CONTRACTS,
            engine_settings=es,
        )
        s = summarize(res)
        if s["max_dd_$"] <= dd_budget and s["net_pnl"] > chosen_pnl:
            chosen = r
            chosen_pnl = s["net_pnl"]
    return chosen if chosen is not None else 0.18


def main():
    print("=" * 100)
    print("PHASE 9B — OOS robustness of top 5 candidates")
    print("=" * 100)
    es = _es_no_blackouts()

    summary_rows = []
    for cid, overrides in CANDIDATES.items():
        p = dict(V1_WINNER_PARAMS)
        p.update(BASE)
        p.update(overrides)
        print(f"\n>>> Candidate {cid}: ssl_len={p['ssl_len']} ssl_mult={p['ssl_mult']} thr={p['sig_extreme_threshold']}")
        chosen_r = find_max_risk_under_dd(p, es)
        print(f"    Chosen risk: {chosen_r:.2f}%")
        full = _run(p, es, chosen_r / 100, f"{cid} FULL")
        y25 = _run(p, es, chosen_r / 100, f"{cid} 2025",
                   start="2025-01-02T00:00", end="2025-12-31T22:59")
        y26 = _run(p, es, chosen_r / 100, f"{cid} 2026",
                   start="2026-01-01T00:00", end="2026-05-22T22:59")
        oos = _run(p, es, chosen_r / 100, f"{cid} OOS (last 3mo)",
                   start="2026-03-01T00:00", end="2026-05-22T22:59")
        summary_rows.append({
            "id": cid,
            "risk_pct": chosen_r,
            "full_pnl": full["net_pnl"],
            "full_dd": full["max_dd_$"],
            "y25_pnl": y25["net_pnl"],
            "y26_pnl": y26["net_pnl"],
            "oos_pnl": oos["net_pnl"],
            "full_pf": full["profit_factor"],
        })

    print()
    print("=" * 100)
    print("CANDIDATE COMPARISON:")
    print("=" * 100)
    print(f"{'ID':<3}  {'risk':>5}  {'full_PnL':>10}  {'full_DD':>9}  "
          f"{'2025':>9}  {'2026':>9}  {'OOS':>9}  {'PF':>5}")
    for s in sorted(summary_rows, key=lambda x: x["full_pnl"], reverse=True):
        print(f"{s['id']:<3}  {s['risk_pct']:>4.2f}%  "
              f"${s['full_pnl']:>9,.0f}  ${s['full_dd']:>8,.0f}  "
              f"${s['y25_pnl']:>8,.0f}  ${s['y26_pnl']:>8,.0f}  "
              f"${s['oos_pnl']:>8,.0f}  {s['full_pf']:>4.2f}")


if __name__ == "__main__":
    main()
