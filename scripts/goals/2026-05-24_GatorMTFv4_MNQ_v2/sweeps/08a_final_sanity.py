"""Phase 8A — final sanity checks before risk tuning.

1) sig_extreme_threshold sweep (case_d uses it; never tested in v1)
2) Re-check cooldown at new config
3) Re-check final_rr fine grid at new config
4) Re-check case bitmask at new config (in case relative ordering shifted)
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
    print(f"  {label:<35s} {fmt_summary(s)}  ({s['elapsed_s']}s)")
    return s


def main():
    print("=" * 100)
    print("PHASE 8A — final sanity checks at v2 best config")
    print("=" * 100)
    es = _es_no_blackouts()
    SEED = dict(V1_WINNER_PARAMS)
    SEED.update(BEST_CONFIG)

    print()
    print("--- sig_extreme_threshold sweep ---")
    for thr in [10, 15, 20, 25, 30, 40, 50]:
        p = dict(SEED)
        p["sig_extreme_threshold"] = thr
        _run(p, es, f"sig_extreme_thr={thr}")

    print()
    print("--- cooldown fine sweep ---")
    for cd in [45, 60, 75, 90, 105, 120, 150]:
        p = dict(SEED)
        p["cooldown_bars"] = cd
        _run(p, es, f"cooldown={cd}")

    print()
    print("--- final_rr fine sweep around 1.5 ---")
    for rr in [1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8]:
        p = dict(SEED)
        p["final_rr"] = rr
        _run(p, es, f"rr={rr}")

    print()
    print("--- case bitmask re-check at v2 best ---")
    for mask in [0b1101, 0b1100, 0b1111, 0b1001, 0b0101, 0b1000]:
        a = bool(mask & 0b1000); b = bool(mask & 0b0100)
        c = bool(mask & 0b0010); d = bool(mask & 0b0001)
        p = dict(SEED)
        p["case_a_on"] = a; p["case_b_on"] = b
        p["case_c_on"] = c; p["case_d_on"] = d
        bits = f"{int(a)}{int(b)}{int(c)}{int(d)}"
        _run(p, es, f"ABCD={bits}")


if __name__ == "__main__":
    main()
