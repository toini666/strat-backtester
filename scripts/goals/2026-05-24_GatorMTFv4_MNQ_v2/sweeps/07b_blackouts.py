"""Phase 7B — cumulative blackout bundle sweep at new best config.

Losing hours: H03 (-3,537), H07 (-2,918), H21 (-2,673), H05 (-1,950),
              H17 (-1,591), H23 (-1,167).

Cumulative bundles (memory: single-hour blackouts often hurt; bundles work):
  - INCR1..6: add losing hours one at a time from biggest loser
  - MORN: H03, H05, H07
  - EVE: H17, H21, H23
  - OVN: H00-H07 (full overnight quiet)
  - OVN+EVE: H00-H07 + H17, H21, H23
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
    "ssl_len": 20, "ssl_mult": 0.20,
}


def _es_with_blackouts(hours):
    """hours = list of integer hour starts (each = 1-hour window).
    Always include the auto-close padding 23:00-23:59 to suppress the
    Sun-open glitch trade that v1 also blocked.
    """
    es = ui_default_engine_settings(STRATEGY)
    for w in es.blackout_windows:
        w.active = False
    from backend.api import BlackoutWindow
    # Insert hours
    seen = {(w.start_hour, w.start_minute, w.end_hour, w.end_minute) for w in es.blackout_windows}
    for h in hours:
        sh, sm = h, 0
        # For hour 23, end at 23:59 (not 24:00)
        if h == 23:
            eh, em = 23, 59
        else:
            eh, em = h + 1, 0
        key = (sh, sm, eh, em)
        if key in seen:
            # Activate existing
            for w in es.blackout_windows:
                if (w.start_hour, w.start_minute, w.end_hour, w.end_minute) == key:
                    w.active = True
        else:
            es.blackout_windows.append(
                BlackoutWindow(active=True, start_hour=sh, start_minute=sm,
                               end_hour=eh, end_minute=em)
            )
            seen.add(key)
    es.auto_close_hour, es.auto_close_minute = AUTO_CLOSE
    return es


def _run(params, es, label):
    t0 = time.time()
    r = run_backtest(
        strategy_name=STRATEGY,
        symbol=SYMBOL, interval=INTERVAL,
        start=START, end=END,
        strategy_params=params,
        initial_equity=INITIAL_EQUITY,
        risk_per_trade=SWEEP_RISK,
        max_contracts=MAX_CONTRACTS,
        engine_settings=es,
    )
    s = summarize(r)
    s["elapsed_s"] = round(time.time() - t0, 1)
    print(f"  {label:<35s} {fmt_summary(s)}  ({s['elapsed_s']}s)")
    return s


def main():
    print("=" * 100)
    print("PHASE 7B — cumulative blackout bundles")
    print("=" * 100)
    SEED = dict(V1_WINNER_PARAMS)
    SEED.update(BEST_CONFIG)

    # Losing hours sorted by magnitude (biggest first)
    LOSERS_ORDER = [3, 7, 21, 5, 17, 23]

    bundles = []
    # Incremental: 1..6 cumulative
    for k in range(1, 7):
        bundles.append((f"INCR-{k}: {LOSERS_ORDER[:k]}", LOSERS_ORDER[:k]))
    # Morning losers
    bundles.append(("MORN: [3,5,7]", [3, 5, 7]))
    # Evening losers
    bundles.append(("EVE: [17,21,23]", [17, 21, 23]))
    # Full overnight quiet (00-07)
    bundles.append(("OVN: [0..7]", list(range(0, 8))))
    # Overnight + evening
    bundles.append(("OVN+EVE: [0..7,17,21,23]", list(range(0, 8)) + [17, 21, 23]))
    # Asia narrow (only 03-07)
    bundles.append(("ASIA-CORE: [3,4,5,6,7]", [3, 4, 5, 6, 7]))
    # Just the v1 winner 9-hour set
    bundles.append(("v1-9HOURS: [6,11,12,14,16,17,19,21,23]",
                    [6, 11, 12, 14, 16, 17, 19, 21, 23]))
    # All losers + h0 prefix (clean overnight)
    bundles.append(("ALL_LOSERS+H0+H1: [0,1,3,5,7,17,21,23]",
                    [0, 1, 3, 5, 7, 17, 21, 23]))

    rows = []
    t_start = time.time()
    # Baseline (no blackouts)
    s = _run(SEED, _es_with_blackouts([]), "BASE (no blackouts)")
    rows.append({"name": "BASE", "hours": [], **s})

    for name, hours in bundles:
        es = _es_with_blackouts(hours)
        s = _run(SEED, es, name)
        rows.append({"name": name, "hours": hours, **s})

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
        print(f"  {r['name']:<40s}  PnL=${r['net_pnl']:>8,.0f}  DD=${r['max_dd_$']:>6,.0f}  "
              f"ratio={ratio:.2f}×  PF={r['profit_factor']}")

    print()
    print("Top 10 by PnL (raw):")
    rows_by_pnl = sorted(rows, key=lambda x: x["net_pnl"], reverse=True)
    for r in rows_by_pnl[:10]:
        ratio = r["net_pnl"] / r["max_dd_$"] if r["max_dd_$"] > 0 else 0
        print(f"  {r['name']:<40s}  PnL=${r['net_pnl']:>8,.0f}  DD=${r['max_dd_$']:>6,.0f}  "
              f"ratio={ratio:.2f}×  PF={r['profit_factor']}")


if __name__ == "__main__":
    main()
