"""Phase 4 — final_rr × cooldown_bars 2-D sweep.

v1 plafonné à RR=2.0; at WR≈37%, RR=3-4 could push PF substantially.
final_rr ∈ {1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 5.0} (7)
cooldown_bars ∈ {30, 60, 90, 120, 180, 240} (6)
= 42 sims.

Best HMA + cases from Phases 2B/3: amp_mult=1.5, h1=13, h2=21, ABCD=1101.
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

BEST_HMA = {"amp_mult": 1.5, "hma1_len": 13, "hma2_len": 21}
BEST_CASES = {"case_a_on": True, "case_b_on": True,
              "case_c_on": False, "case_d_on": True}


def _es_no_blackouts():
    es = ui_default_engine_settings(STRATEGY)
    for w in es.blackout_windows:
        w.active = False
    es.auto_close_hour, es.auto_close_minute = AUTO_CLOSE
    return es


def main():
    print("=" * 100)
    print("PHASE 4 — final_rr × cooldown_bars sweep")
    print("=" * 100)
    print(f"Best HMA: {BEST_HMA}, ABCD=1101")
    print()

    es = _es_no_blackouts()
    SEED = dict(V1_WINNER_PARAMS)
    SEED.update(BEST_HMA)
    SEED.update(BEST_CASES)

    rrs = [1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 5.0]
    cds = [30, 60, 90, 120, 180, 240]

    rows = []
    t_start = time.time()
    for rr in rrs:
        for cd in cds:
            p = dict(SEED)
            p["final_rr"] = rr
            p["cooldown_bars"] = cd
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
                print(f"  rr={rr:<3}  cd={cd:>3}  {fmt_summary(s)}  ({s['elapsed_s']}s)")
                rows.append({"rr": rr, "cd": cd, **s})
            except Exception as exc:
                print(f"  rr={rr} cd={cd}  ERROR: {exc}")

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
        print(f"  rr={r['rr']:<3}  cd={r['cd']:>3}  "
              f"PnL=${r['net_pnl']:>9,.0f}  DD=${r['max_dd_$']:>6,.0f}  "
              f"ratio={ratio:.2f}×  N={r['trades']:>4}  WR={r['win_rate']:>4.1f}%  PF={r['profit_factor']}")

    print()
    print("Top 10 by raw PnL (ignore DD):")
    rows_pnl = sorted(rows, key=lambda x: x["net_pnl"], reverse=True)
    for r in rows_pnl[:10]:
        ratio = r["net_pnl"] / r["max_dd_$"] if r["max_dd_$"] > 0 else 0
        print(f"  rr={r['rr']:<3}  cd={r['cd']:>3}  "
              f"PnL=${r['net_pnl']:>9,.0f}  DD=${r['max_dd_$']:>6,.0f}  "
              f"ratio={ratio:.2f}×  N={r['trades']:>4}  PF={r['profit_factor']}")


if __name__ == "__main__":
    main()
