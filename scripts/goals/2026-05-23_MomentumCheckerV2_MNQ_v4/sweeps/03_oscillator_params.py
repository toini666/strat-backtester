"""Phase 3 — Oscillator core params + indicator lengths.

Memory note: mf_length and mf_smooth are non-monotone on HMASSLOsciV3 —
worth fine sweep on MCV2 too. hyper_wave_length / signal_length /
signal_type drive the SIG/SGD curves that all the filters key off.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from scripts.goals._shared.harness import run_backtest, summarize, fmt_summary
from sweeps._campaign import (
    END, INITIAL_EQUITY, INTERVAL, MAX_CONTRACTS,
    SEED_PARAMS, SEED_RISK, START, STRATEGY, SYMBOL,
    make_engine_settings,
)


def run(label, overrides):
    params = dict(SEED_PARAMS); params.update(overrides)
    result = run_backtest(
        strategy_name=STRATEGY, symbol=SYMBOL, interval=INTERVAL,
        start=START, end=END, strategy_params=params,
        initial_equity=INITIAL_EQUITY, risk_per_trade=SEED_RISK,
        max_contracts=MAX_CONTRACTS, engine_settings=make_engine_settings(),
    )
    s = summarize(result); s["label"] = label
    print(f"{label:<48s} {fmt_summary(s)}")
    return s


def main():
    print("=" * 140)
    print("Phase 3 — Oscillator + indicator lengths")
    print("Seed: PnL $75,132 / DD $2,420 / WR 39.6%")
    print("=" * 140)

    print("\n--- 3A. mf_length (seed=35) — non-monotone per memory ---")
    for v in [10, 15, 20, 25, 30, 35, 40, 45, 50, 60, 80, 100]:
        run(f"mf_length={v}", {"mf_length": v})

    print("\n--- 3B. mf_smooth (seed=5) ---")
    for v in [1, 2, 3, 4, 5, 6, 7, 9, 12, 15]:
        run(f"mf_smooth={v}", {"mf_smooth": v})

    print("\n--- 3C. hyper_wave_length (seed=5) ---")
    for v in [2, 3, 4, 5, 6, 7, 8, 10, 12]:
        run(f"hyper_wave_length={v}", {"hyper_wave_length": v})

    print("\n--- 3D. signal_length (seed=3) ---")
    for v in [1, 2, 3, 4, 5, 7, 9]:
        run(f"signal_length={v}", {"signal_length": v})

    print("\n--- 3E. signal_type ---")
    for t in ["SMA", "EMA"]:
        run(f"signal_type={t}", {"signal_type": t})

    print("\n--- 3F. hw_extreme (seed=20) ---")
    for v in [10, 12, 15, 18, 20, 22, 25, 30]:
        run(f"hw_extreme={v}", {"hw_extreme": v})

    print("\n--- 3G. max_candle_pct (seed=0.3) ---")
    for v in [0.15, 0.2, 0.25, 0.3, 0.35, 0.4, 0.5, 0.6]:
        run(f"max_candle_pct={v}", {"max_candle_pct": v})

    print("\n--- 3H. delta_off_mode ---")
    for m in ["both", "counter_trend"]:
        run(f"delta_off_mode={m}", {"delta_off_mode": m})


if __name__ == "__main__":
    main()
