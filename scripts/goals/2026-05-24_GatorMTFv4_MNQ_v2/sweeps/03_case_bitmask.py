"""Phase 3 — full 16 case bitmask sweep at best HMA config.

Best HMA from Phase 2B: amp_mult=1.5 (h1=13, h2=21 unchanged).
v1 only tested 1111 and 1101. Try all 16 to find restrictive combos
that boost PF (memory: project_gatormtfv4_mfi_inert says MFI becomes a real
filter when cases are disabled).
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


def _es_no_blackouts():
    es = ui_default_engine_settings(STRATEGY)
    for w in es.blackout_windows:
        w.active = False
    es.auto_close_hour, es.auto_close_minute = AUTO_CLOSE
    return es


def main():
    print("=" * 100)
    print("PHASE 3 — 16 case bitmask sweep")
    print("=" * 100)
    print(f"Best HMA from Phase 2B: {BEST_HMA}")
    print()

    es = _es_no_blackouts()
    SEED = dict(V1_WINNER_PARAMS)
    SEED.update(BEST_HMA)

    rows = []
    t_start = time.time()
    for mask in range(16):
        a = bool(mask & 0b1000)
        b = bool(mask & 0b0100)
        c = bool(mask & 0b0010)
        d = bool(mask & 0b0001)
        # Skip zero mask (no cases active)
        if not (a or b or c or d):
            print(f"  mask={mask:>2} 0000  SKIP (no cases)")
            continue
        p = dict(SEED)
        p["case_a_on"] = a
        p["case_b_on"] = b
        p["case_c_on"] = c
        p["case_d_on"] = d
        bits = f"{int(a)}{int(b)}{int(c)}{int(d)}"
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
            print(f"  ABCD={bits}  {fmt_summary(s)}  ({s['elapsed_s']}s)")
            rows.append({"mask": mask, "bits": bits, **s})
        except Exception as exc:
            print(f"  ABCD={bits}  ERROR: {exc}")

    print()
    print(f"Total elapsed: {(time.time() - t_start)/60:.1f} min  ({len(rows)} sims)")

    print()
    print("=" * 100)
    print("Top 5 by PnL/DD ratio:")
    print("=" * 100)
    rows_valid = [r for r in rows if r["max_dd_$"] > 0]
    rows_valid.sort(key=lambda x: x["net_pnl"] / x["max_dd_$"], reverse=True)
    for r in rows_valid[:5]:
        ratio = r["net_pnl"] / r["max_dd_$"]
        print(f"  ABCD={r['bits']}  PnL=${r['net_pnl']:>9,.0f}  DD=${r['max_dd_$']:>6,.0f}  "
              f"ratio={ratio:.2f}×  N={r['trades']:>4}  WR={r['win_rate']:>4.1f}%  PF={r['profit_factor']}")


if __name__ == "__main__":
    main()
