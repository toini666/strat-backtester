"""Phase 8C — refine sig_extreme_thr around 35, plus alternate combos.

8B found thr=35 rr=1.5 = ratio 7.03× (PnL $35.9k / DD $5.1k / PF 1.13).
Confirm the peak and check if nearby (thr, rr, cd) combos do even better.
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
    "sig_extreme_threshold": 35.0,
}


def _es_no_blackouts():
    es = ui_default_engine_settings(STRATEGY)
    for w in es.blackout_windows:
        w.active = False
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
    print(f"  {label:<32s} {fmt_summary(s)}  ({s['elapsed_s']}s)")
    return s


def main():
    print("=" * 100)
    print("PHASE 8C — sig_extreme_thr refine around 35")
    print("=" * 100)
    es = _es_no_blackouts()
    SEED = dict(V1_WINNER_PARAMS)
    SEED.update(BEST_CONFIG)

    # Finer thr grid
    print()
    print("--- thr fine sweep ---")
    rows = []
    for thr in [28, 31, 33, 35, 37, 39, 42, 45]:
        p = dict(SEED)
        p["sig_extreme_threshold"] = thr
        s = _run(p, es, f"thr={thr}")
        rows.append({"thr": thr, **s})

    print()
    print("--- thr × cooldown combo (cd ∈ {85, 90, 95, 100}) ---")
    for thr in [33, 35, 37]:
        for cd in [85, 90, 95, 100]:
            p = dict(SEED)
            p["sig_extreme_threshold"] = thr
            p["cooldown_bars"] = cd
            s = _run(p, es, f"thr={thr} cd={cd}")
            rows.append({"thr": thr, "cd": cd, **s})

    print()
    print("--- thr × hyper_wave_length and signal_length spot-check ---")
    for hwL in [3, 5, 7]:
        for sL in [2, 3, 4]:
            p = dict(SEED)
            p["sig_extreme_threshold"] = 35
            p["hyper_wave_length"] = hwL
            p["signal_length"] = sL
            s = _run(p, es, f"hwL={hwL} sL={sL}")
            rows.append({"hwL": hwL, "sL": sL, **s})

    print()
    print("=" * 100)
    print("Top 10 by PnL/DD ratio:")
    print("=" * 100)
    rows_valid = [r for r in rows if r["max_dd_$"] > 0]
    rows_valid.sort(key=lambda x: x["net_pnl"] / x["max_dd_$"], reverse=True)
    for r in rows_valid[:10]:
        ratio = r["net_pnl"] / r["max_dd_$"]
        label_keys = [k for k in r if k not in {"label", "elapsed_s", "net_pnl", "trades",
                                                  "win_rate", "sl_rate", "be_rate",
                                                  "loss_other_rate", "max_dd_$", "max_dd_%",
                                                  "profit_factor", "avg_win", "avg_loss",
                                                  "sharpe"}]
        params_str = " ".join(f"{k}={r[k]}" for k in label_keys)
        print(f"  {params_str:<32s}  PnL=${r['net_pnl']:>8,.0f}  DD=${r['max_dd_$']:>6,.0f}  "
              f"ratio={ratio:.2f}×  PF={r['profit_factor']}")


if __name__ == "__main__":
    main()
