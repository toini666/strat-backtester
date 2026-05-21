"""Phase 8 — Combo lattice exploiting Phase 6 ema_prin=15 finding.

Key Phase 6 finding: ema_prin=15 cluster gives PnL +$5-6k but DD +$636.
We need to find (ema_prin=15) × (lower risk OR alt sl_max OR more blackouts)
that keeps DD ≤ $2,500 while beating seed PnL.

Also stack: BO 15:30-17 (Phase 7 +$385 PnL), max_candle=0.25 (Phase 3 -$52 DD).

~45 sims.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

CAMPAIGN_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CAMPAIGN_DIR / "sweeps"))

from scripts.goals._shared.harness import run_backtest, summarize, fmt_summary  # noqa: E402

from _campaign import (  # noqa: E402
    BASELINE_PARAMS, END, INITIAL_EQUITY, INTERVAL, MAX_CONTRACTS,
    RISK_PER_TRADE, START, STRATEGY, SYMBOL, seed_engine, build_engine,
)


def bo_seed():
    return seed_engine()


def bo_with_1530_17():
    return build_engine([
        (12, 30, 14, 0), (15, 30, 17, 0),
        (18, 0, 19, 0), (20, 0, 21, 0), (22, 0, 23, 59),
    ])


def run(label, params, engine, risk):
    r = run_backtest(
        strategy_name=STRATEGY, symbol=SYMBOL, interval=INTERVAL,
        start=START, end=END,
        initial_equity=INITIAL_EQUITY, risk_per_trade=risk,
        max_contracts=MAX_CONTRACTS,
        engine_settings=engine,
        strategy_params=params,
    )
    s = summarize(r)
    s["label"] = label
    tag = ""
    if s["max_dd_$"] < 2000 and s["net_pnl"] >= 55_000:
        tag = " ⭐ DD<$2k"
    elif s["max_dd_$"] < 2500 and s["net_pnl"] > 58_249:
        tag = " 🏆 PnL>seed"
    elif s["max_dd_$"] < 2500 and s["net_pnl"] > 56_000:
        tag = " ✓"
    print(f"{label:<70s} {fmt_summary(s)}{tag}")
    return s


def main() -> int:
    print("=" * 110)
    print("PHASE 8 — Combo lattice (ema_prin=15 family × risk × blackouts × mcp)")
    print("=" * 110)

    base = dict(BASELINE_PARAMS)

    print("\n--- 8A: ema_prin=15 ema_sec=7 × risk (find DD≤$2500 cell) ---")
    for r in [0.0040, 0.0042, 0.0044, 0.0045, 0.0047, 0.0048, 0.0050, 0.0052, 0.0053, 0.0055]:
        p = dict(base)
        p["ema_prin_len"] = 15
        p["ema_sec_len"] = 7
        run(f"ema_prin=15 ema_sec=7 r={r*100:.3f}%", p, bo_seed(), r)

    print("\n--- 8B: ema_prin=15 ema_sec=5 × risk (alt) ---")
    for r in [0.0042, 0.0045, 0.0048, 0.0050, 0.0053]:
        p = dict(base)
        p["ema_prin_len"] = 15
        p["ema_sec_len"] = 5
        run(f"ema_prin=15 ema_sec=5 r={r*100:.3f}%", p, bo_seed(), r)

    print("\n--- 8C: ema_prin=15 ema_sec=7 × sl_max alts at r=0.45-0.50% ---")
    for sl_max in [60, 70, 80, 90, 100, 120]:
        for r in [0.0045, 0.0050]:
            p = dict(base)
            p["ema_prin_len"] = 15
            p["ema_sec_len"] = 7
            p["sl_max_points"] = float(sl_max)
            run(f"ema=15/7 sl_max={sl_max} r={r*100:.3f}%", p, bo_seed(), r)

    print("\n--- 8D: ema_prin=15 ema_sec=7 + BO 15:30-17 + risk ---")
    for r in [0.0045, 0.0048, 0.0050, 0.0053, 0.0055]:
        p = dict(base)
        p["ema_prin_len"] = 15
        p["ema_sec_len"] = 7
        run(f"ema=15/7 +BO15:30 r={r*100:.3f}%", p, bo_with_1530_17(), r)

    print("\n--- 8E: ema_prin=15 ema_sec=7 + mcp=0.25 + risk ---")
    for r in [0.0045, 0.0048, 0.0050, 0.0053]:
        p = dict(base)
        p["ema_prin_len"] = 15
        p["ema_sec_len"] = 7
        p["max_candle_pct"] = 0.25
        run(f"ema=15/7 mcp=0.25 r={r*100:.3f}%", p, bo_seed(), r)

    print("\n--- 8F: seed + BO 15:30-17 + mcp=0.25 (free PnL stack at seed risk) ---")
    for r in [0.0050, 0.0053, 0.0055]:
        p = dict(base)
        p["max_candle_pct"] = 0.25
        run(f"seed+BO15:30+mcp=0.25 r={r*100:.3f}%", p, bo_with_1530_17(), r)

    print("\n--- 8G: alt_robust (sl_max=70, r=0.53%) + mcp=0.25 + BO 15:30 ---")
    for r in [0.0053, 0.0055]:
        for sl_max in [70, 80]:
            p = dict(base)
            p["sl_max_points"] = float(sl_max)
            p["max_candle_pct"] = 0.25
            run(f"sl_max={sl_max} mcp=0.25 r={r*100:.3f}%", p, bo_seed(), r)
            p2 = dict(p)
            run(f"sl_max={sl_max} mcp=0.25 +BO15:30 r={r*100:.3f}%", p2, bo_with_1530_17(), r)

    return 0


if __name__ == "__main__":
    sys.exit(main())
