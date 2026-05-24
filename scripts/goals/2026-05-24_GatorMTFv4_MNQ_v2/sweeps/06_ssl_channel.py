"""Phase 6 — SSL Keltner channel ssl_len × ssl_mult sweep.

Never touched in v1. SSL gates the HMA cross — tighter channel = more
crosses, fewer high-conviction; wider = fewer but quality.

ssl_len ∈ {20, 30, 40, 60, 80, 100, 140} (7)
ssl_mult ∈ {0.10, 0.15, 0.20, 0.30, 0.40, 0.60} (6)
= 42 sims at current best config.
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
    V1_WINNER_PARAMS, SWEEP_RISK, AUTO_CLOSE,
    START, END, SYMBOL, INTERVAL, STRATEGY,
    INITIAL_EQUITY, MAX_CONTRACTS,
)

BEST_CONFIG = {
    "amp_mult": 1.5, "hma1_len": 13, "hma2_len": 21,
    "case_a_on": True, "case_b_on": True,
    "case_c_on": False, "case_d_on": True,
    "final_rr": 1.5, "cooldown_bars": 90,
    "sl_lookback": 15, "tick_buffer": 6,
}


def _es_no_blackouts():
    es = ui_default_engine_settings(STRATEGY)
    for w in es.blackout_windows:
        w.active = False
    es.auto_close_hour, es.auto_close_minute = AUTO_CLOSE
    return es


def main():
    print("=" * 100)
    print("PHASE 6 — SSL Keltner ssl_len × ssl_mult")
    print("=" * 100)
    es = _es_no_blackouts()
    SEED = dict(V1_WINNER_PARAMS)
    SEED.update(BEST_CONFIG)

    ssl_lens = [20, 30, 40, 60, 80, 100, 140]
    ssl_mults = [0.10, 0.15, 0.20, 0.30, 0.40, 0.60]

    rows = []
    t_start = time.time()
    for slen in ssl_lens:
        for smult in ssl_mults:
            p = dict(SEED)
            p["ssl_len"] = slen
            p["ssl_mult"] = smult
            t0 = time.time()
            try:
                r = run_backtest(
                    strategy_name=STRATEGY,
                    symbol=SYMBOL, interval=INTERVAL,
                    start=START, end=END,
                    strategy_params=p,
                    initial_equity=INITIAL_EQUITY,
                    risk_per_trade=SWEEP_RISK,
                    max_contracts=MAX_CONTRACTS,
                    engine_settings=es,
                )
                s = summarize(r)
                s["elapsed_s"] = round(time.time() - t0, 1)
                print(f"  slen={slen:>3} smult={smult:.2f}  {fmt_summary(s)}  ({s['elapsed_s']}s)")
                rows.append({"ssl_len": slen, "ssl_mult": smult, **s})
            except Exception as exc:
                print(f"  slen={slen} smult={smult}  ERROR: {exc}")

    print()
    print(f"Total elapsed: {(time.time() - t_start)/60:.1f} min  ({len(rows)} sims)")

    print()
    print("=" * 100)
    print("Top 10 by PnL/DD ratio:")
    print("=" * 100)
    rows_valid = [r for r in rows if r["max_dd_$"] > 0]
    rows_valid.sort(key=lambda x: x["net_pnl"] / x["max_dd_$"], reverse=True)
    for r in rows_valid[:10]:
        ratio = r["net_pnl"] / r["max_dd_$"]
        print(f"  slen={r['ssl_len']:>3} smult={r['ssl_mult']:.2f}  "
              f"PnL=${r['net_pnl']:>8,.0f}  DD=${r['max_dd_$']:>6,.0f}  "
              f"ratio={ratio:.2f}×  N={r['trades']:>4}  WR={r['win_rate']:>4.1f}%  PF={r['profit_factor']}")


if __name__ == "__main__":
    main()
