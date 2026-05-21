"""Phase 0 — Reproduce seed preset + hour diagnostic + blackout baseline pick.

Two anchors compared at the top:
  - SEED engine (4 surgical blackouts from prior winner)
  - MINIMAL engine (only 22-23:59 close lock)

Whichever has higher PnL/DD trade-off picks the anchor for subsequent
phases. Hour-of-day diagnostic on minimal engine reveals losing buckets
to surgically blackout in Phase 7.
"""

from __future__ import annotations

import sys
import time
from collections import defaultdict
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

CAMPAIGN_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CAMPAIGN_DIR / "sweeps"))

from scripts.goals._shared.harness import run_backtest, summarize, fmt_summary  # noqa: E402

from _campaign import (  # noqa: E402
    BASELINE_PARAMS, END, INITIAL_EQUITY, INTERVAL, MAX_CONTRACTS,
    RISK_PER_TRADE, START, STRATEGY, SYMBOL, SEED_PNL, SEED_DD,
    seed_engine, minimal_engine,
)


def main() -> int:
    print("=" * 110)
    print("PHASE 0 — Reproduce seed + diagnostic + minimal-engine comparison")
    print("=" * 110)
    print(f"Target seed: PnL≈${SEED_PNL:,.0f} / $DD≈${SEED_DD:,.0f}")

    # 1. Reproduce seed
    t0 = time.time()
    result = run_backtest(
        strategy_name=STRATEGY, symbol=SYMBOL, interval=INTERVAL,
        start=START, end=END,
        initial_equity=INITIAL_EQUITY, risk_per_trade=RISK_PER_TRADE,
        max_contracts=MAX_CONTRACTS,
        engine_settings=seed_engine(),
        strategy_params=BASELINE_PARAMS,
    )
    s_seed = summarize(result)
    elapsed = time.time() - t0
    print(f"\n[seed replay]            {fmt_summary(s_seed)}  ({elapsed:.1f}s)")

    pnl_delta = s_seed["net_pnl"] - SEED_PNL
    dd_delta = s_seed["max_dd_$"] - SEED_DD
    print(f"\nDelta vs seed: PnL {pnl_delta:+,.0f}  /  $DD {dd_delta:+,.0f}")
    if abs(pnl_delta) > 50 or abs(dd_delta) > 50:
        print("❌ BASELINE MISMATCH (>$50) — must investigate before sweeping")
    else:
        print("✅ Baseline matches seed within $50")

    # 2. Minimal engine (only 22-23:59 lock)
    t0 = time.time()
    result_min = run_backtest(
        strategy_name=STRATEGY, symbol=SYMBOL, interval=INTERVAL,
        start=START, end=END,
        initial_equity=INITIAL_EQUITY, risk_per_trade=RISK_PER_TRADE,
        max_contracts=MAX_CONTRACTS,
        engine_settings=minimal_engine(),
        strategy_params=BASELINE_PARAMS,
    )
    s_min = summarize(result_min)
    elapsed = time.time() - t0
    print(f"[minimal engine]         {fmt_summary(s_min)}  ({elapsed:.1f}s)")

    # 3. Hour-of-day diagnostic on minimal engine
    trades = [t for t in result_min["trades"] if not t.get("excluded", False)]
    longs = [t for t in trades if t.get("direction", "").lower() == "long"]
    shorts = [t for t in trades if t.get("direction", "").lower() == "short"]

    def _stats(tr):
        if not tr:
            return "n=0"
        pnls = [t["pnl"] for t in tr]
        wins = [p for p in pnls if p > 0]
        return (f"n={len(tr):>4}  PnL=${sum(pnls):>+8,.0f}  "
                f"WR={len(wins)/len(tr)*100:>5.1f}%  "
                f"avg=${sum(pnls)/len(tr):>+7,.0f}")

    print("\n--- by direction (minimal engine) ---")
    print(f"  Long:   {_stats(longs)}")
    print(f"  Short:  {_stats(shorts)}")

    by_hour = defaultdict(list)
    for t in trades:
        h = pd.to_datetime(t["entry_time"]).hour
        by_hour[h].append(t["pnl"])

    print("\n--- by hour-of-day (entry, Brussels, minimal engine) ---")
    print(f"{'Hour':<6}{'n':>5}{'total':>12}{'avg':>10}{'WR':>8}")
    for h in sorted(by_hour):
        pnls = by_hour[h]
        wins = [p for p in pnls if p > 0]
        wr = len(wins) / len(pnls) * 100 if pnls else 0
        print(f"H={h:02d}  {len(pnls):>5}  ${sum(pnls):>+10,.0f}  ${sum(pnls)/len(pnls):>+7,.0f}  {wr:>5.0f}%")

    by_dow = defaultdict(list)
    for t in trades:
        dow = pd.to_datetime(t["entry_time"]).day_name()
        by_dow[dow].append(t["pnl"])

    print("\n--- by day-of-week (minimal engine) ---")
    print(f"{'DOW':<12}{'n':>5}{'total':>12}{'avg':>10}{'WR':>8}")
    for d in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Sunday"]:
        pnls = by_dow.get(d, [])
        if not pnls:
            continue
        wins = [p for p in pnls if p > 0]
        wr = len(wins) / len(pnls) * 100
        print(f"{d:<12}{len(pnls):>5}  ${sum(pnls):>+10,.0f}  ${sum(pnls)/len(pnls):>+7,.0f}  {wr:>5.0f}%")

    # Underwater duration approx (worst peak-to-trough trade index)
    eq = result["equity_curve"]
    if eq:
        peak = eq[0]["equity"]
        peak_idx = 0
        worst_dd = 0.0
        worst_peak_idx, worst_trough_idx = 0, 0
        for i, e in enumerate(eq):
            v = e["equity"]
            if v > peak:
                peak = v
                peak_idx = i
            dd = peak - v
            if dd > worst_dd:
                worst_dd = dd
                worst_peak_idx = peak_idx
                worst_trough_idx = i
        if eq:
            print(f"\n--- worst DD location (seed engine) ---")
            print(f"  peak @ {eq[worst_peak_idx].get('timestamp', '?')}  ${eq[worst_peak_idx]['equity']:,.0f}")
            print(f"  trough @ {eq[worst_trough_idx].get('timestamp', '?')}  ${eq[worst_trough_idx]['equity']:,.0f}")
            print(f"  $ drop = ${worst_dd:,.0f}")

    # Decision
    print("\n" + "=" * 110)
    print("ANCHOR PICK")
    print("=" * 110)
    print(f"  seed engine    : PnL=${s_seed['net_pnl']:>9,.0f}  DD=${s_seed['max_dd_$']:>6,.0f}  P/DD={s_seed['net_pnl']/s_seed['max_dd_$']:.2f}")
    print(f"  minimal engine : PnL=${s_min['net_pnl']:>9,.0f}  DD=${s_min['max_dd_$']:>6,.0f}  P/DD={s_min['net_pnl']/s_min['max_dd_$']:.2f}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
