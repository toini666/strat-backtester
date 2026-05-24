"""Phase 8 — Final Pareto crystallization.

New anchor (Phase 7 best DD-safe):
  ema_prin_len=34 + ema_sec_len=18 + st_atr=14 + tick_buffer=0
  + sl_max_points=42 + BO+07-08

Goals:
  - Map the risk cliff at 0.65→0.66 with sl_max ∈ {41, 42, 43}
  - Confirm independence (or compounding) of ema_prin=34, ema_sec=18 combo
  - Identify the WINNER + 2-3 alternatives
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from scripts.goals._shared.harness import run_backtest, summarize, fmt_summary
from sweeps._campaign import (
    END, INITIAL_EQUITY, INTERVAL, MAX_CONTRACTS,
    SEED_PARAMS, SEED_RISK, SEED_BLACKOUTS, START, STRATEGY, SYMBOL,
    make_engine_settings,
)


BO_0708 = [
    {"active": True, "start_hour": 7, "start_minute": 0,
     "end_hour": 8, "end_minute": 0},
]


NEW_ANCHOR = {
    "ema_prin_len": 34, "ema_sec_len": 18, "st_atr": 14,
    "tick_buffer": 0, "sl_max_points": 42,
}


def run(label, overrides=None, risk=None):
    params = dict(SEED_PARAMS); params.update(NEW_ANCHOR)
    if overrides:
        params.update(overrides)
    r = risk if risk is not None else SEED_RISK
    result = run_backtest(
        strategy_name=STRATEGY, symbol=SYMBOL, interval=INTERVAL,
        start=START, end=END, strategy_params=params,
        initial_equity=INITIAL_EQUITY, risk_per_trade=r,
        max_contracts=MAX_CONTRACTS,
        engine_settings=make_engine_settings(blackouts=SEED_BLACKOUTS + BO_0708),
    )
    s = summarize(result); s["label"] = label
    print(f"{label:<60s} {fmt_summary(s)}")
    return s


def main():
    print("=" * 140)
    print("Phase 8 — Final Pareto crystallization")
    print("Anchor: ema_prin=34, ema_sec=18, st_atr=14, tb=0, sl_max=42 + BO+07-08")
    print("=" * 140)

    print("\n--- 8A. Anchor + risk fine band ---")
    for r in [0.58, 0.60, 0.61, 0.62, 0.63, 0.64, 0.65]:
        run(f"anchor risk={r}%", risk=r / 100)

    print("\n--- 8B. Cliff exploration (risk 0.65-0.67) ---")
    for r in [0.650, 0.655, 0.660, 0.665, 0.670]:
        run(f"anchor risk={r}%", risk=r / 100)

    print("\n--- 8C. sl_max around 42 with risk=0.62 ---")
    for v in [40, 41, 42, 43, 44]:
        run(f"sl_max={v} r=0.62%", {"sl_max_points": v}, risk=0.0062)

    print("\n--- 8D. ema_prin_len final around 34 with new anchor ---")
    for v in [32, 33, 34, 35]:
        run(f"ema_prin={v}", {"ema_prin_len": v})

    print("\n--- 8E. ema_sec_len final around 18 ---")
    for v in [15, 16, 17, 18, 19, 20]:
        run(f"ema_sec={v}", {"ema_sec_len": v})

    print("\n--- 8F. Combined ema_prin × ema_sec with new anchor ---")
    for prin in [33, 34, 35]:
        for sec in [15, 18, 20]:
            run(f"prin={prin} sec={sec}",
                {"ema_prin_len": prin, "ema_sec_len": sec})

    print("\n--- 8G. Final candidates summary ---")
    # WINNER candidate 1: DD-strict, max-PnL under DD<=$2,420
    run("WIN-DDSAFE risk=0.62 ema=34 sec=18 sl42", risk=0.0062)
    # WINNER candidate 2: relaxed DD (~$2,500) for higher PnL
    run("WIN-MID risk=0.65 ema=34 sec=18 sl42", risk=0.0065)
    # WINNER candidate 3: cross the cliff for max-PnL
    run("WIN-RISKY risk=0.66 ema=34 sec=18 sl42", risk=0.0066)


if __name__ == "__main__":
    main()
