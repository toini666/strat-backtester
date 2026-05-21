"""Phase 9 — Fine risk-band exploration around Phase 8 winners.

Anchor 1 (MAX-PNL):  seed + BO15:30 + mcp=0.25 @ r near 0.55%
Anchor 2 (LOW-DD):   sl_max=80 + mcp=0.25 + BO15:30 @ r near 0.53%

Also push for DD<$2,000:
  - sl_max in {60, 70, 80, 90} × mcp=0.25 × BO15:30 × r in {0.30, 0.40, 0.45, 0.50}
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

CAMPAIGN_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CAMPAIGN_DIR / "sweeps"))

from scripts.goals._shared.harness import run_backtest, summarize, fmt_summary  # noqa: E402

from _campaign import (  # noqa: E402
    BASELINE_PARAMS, END, INITIAL_EQUITY, INTERVAL, MAX_CONTRACTS,
    START, STRATEGY, SYMBOL, seed_engine, build_engine,
)


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
    if s["max_dd_$"] < 2000 and s["net_pnl"] >= 45_000:
        tag = " ⭐ DD<$2k"
    elif s["max_dd_$"] < 2500 and s["net_pnl"] > 58_625:
        tag = " 🏆 PnL>P8winner"
    elif s["max_dd_$"] < 2200 and s["net_pnl"] >= 50_000:
        tag = " 💎 robust"
    print(f"{label:<75s} {fmt_summary(s)}{tag}")
    return s


def main() -> int:
    print("=" * 110)
    print("PHASE 9 — Fine risk-band exploration around P8 winners")
    print("=" * 110)

    base = dict(BASELINE_PARAMS)
    base["max_candle_pct"] = 0.25

    print("\n--- 9A: P8 WINNER fine risk-band (seed sl_max + mcp=0.25 + BO15:30) ---")
    for r in [0.0050, 0.0052, 0.0053, 0.0054, 0.0055, 0.0056, 0.0057, 0.0058, 0.0060]:
        p = dict(base)
        run(f"P8W sl_max=100 r={r*100:.3f}%", p, bo_with_1530_17(), r)

    print("\n--- 9B: P8 LOW-DD fine risk-band (sl_max=80 + mcp=0.25 + BO15:30) ---")
    for r in [0.0048, 0.0050, 0.0052, 0.0053, 0.0054, 0.0055, 0.0056, 0.0058]:
        p = dict(base)
        p["sl_max_points"] = 80.0
        run(f"sl_max=80 r={r*100:.3f}%", p, bo_with_1530_17(), r)

    print("\n--- 9C: push for DD<$2k (low-risk × sl_max alts) ---")
    for sl_max in [60, 70, 80, 90]:
        for r in [0.0030, 0.0035, 0.0040, 0.0045, 0.0050]:
            p = dict(base)
            p["sl_max_points"] = float(sl_max)
            run(f"sl_max={sl_max} r={r*100:.3f}%", p, bo_with_1530_17(), r)

    print("\n--- 9D: tighter mcp + BO + risk (push DD<$2k harder) ---")
    for mcp in [0.20, 0.22, 0.25]:
        for r in [0.0045, 0.0050, 0.0053]:
            p = dict(base)
            p["max_candle_pct"] = mcp
            p["sl_max_points"] = 80.0
            run(f"sl_max=80 mcp={mcp} r={r*100:.3f}%", p, bo_with_1530_17(), r)

    return 0


if __name__ == "__main__":
    sys.exit(main())
