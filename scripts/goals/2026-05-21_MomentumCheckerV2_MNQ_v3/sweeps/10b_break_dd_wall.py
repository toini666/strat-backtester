"""Phase 10b (v3) — Last-ditch attempts to break DD<$2,500 + PnL≥$80,565.

The cliff at risk 0.63→0.64% is rounding-driven. Two angles:
  A. Shift the cliff by changing average SL distance (sl_max, tick_buffer)
  B. Cut the worst-DD event with a wider Asia blackout

Tight ~30-sim budget to stay within 500-sim total.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

CAMPAIGN_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CAMPAIGN_DIR / "sweeps"))

from scripts.goals._shared.harness import bench  # noqa: E402

from _campaign import (  # noqa: E402
    BASELINE_PARAMS, END, INITIAL_EQUITY, INTERVAL, MAX_CONTRACTS,
    START, STRATEGY, SYMBOL, build_engine, seed_engine,
)

P6_ANCHOR = dict(BASELINE_PARAMS)
P6_ANCHOR.update({
    "sl_max_points": 40.0,
    "tick_buffer": 2,
    "pts_ema_align": 2,
    "min_gap": 10,
})


def _common(engine, risk):
    return dict(
        strategy_name=STRATEGY, symbol=SYMBOL, interval=INTERVAL,
        start=START, end=END,
        initial_equity=INITIAL_EQUITY, risk_per_trade=risk,
        max_contracts=MAX_CONTRACTS, engine_settings=engine,
    )


def _override(**kw):
    p = dict(P6_ANCHOR)
    p.update(kw)
    return p


def main() -> int:
    print("=" * 110)
    print("PHASE 10b (v3) — Break DD<$2,500 + PnL≥$80,565")
    print("=" * 110)

    results = []
    t0 = time.time()

    eng_seed = seed_engine()
    eng_23_03 = build_engine([(23, 0, 23, 59), (0, 0, 3, 0), (9, 0, 10, 0),
                              (13, 0, 14, 30), (17, 0, 23, 59)])
    eng_00_03 = build_engine([(0, 0, 3, 0), (9, 0, 10, 0),
                              (13, 0, 14, 30), (17, 0, 23, 59)])
    eng_01_03 = build_engine([(1, 0, 3, 0), (9, 0, 10, 0),
                              (13, 0, 14, 30), (17, 0, 23, 59)])
    eng_01_02 = build_engine([(1, 0, 2, 0), (9, 0, 10, 0),
                              (13, 0, 14, 30), (17, 0, 23, 59)])

    # --- A: shift the cliff via sl_max & tick_buffer ---
    print("\n--- A: shift the rounding cliff ---")
    for sl_max in [38.0, 42.0, 45.0]:
        for r in [0.0063, 0.0064, 0.0065]:
            label = f"sl_max={sl_max} tb=2 r={r*100:.2f}%"
            s = bench(label, strategy_params=_override(sl_max_points=sl_max),
                      **_common(eng_seed, r))
            results.append((label, s))

    # tb fine sweep at sl_max=40
    for tb in [1, 3, 4]:
        for r in [0.0064, 0.0065]:
            label = f"sl_max=40 tb={tb} r={r*100:.2f}%"
            s = bench(label, strategy_params=_override(tick_buffer=tb),
                      **_common(eng_seed, r))
            results.append((label, s))

    # --- B: wider Asia blackouts × risk ---
    print("\n--- B: wider Asia blackouts ---")
    for label_bo, engine in [
        ("23-03", eng_23_03),
        ("00-03", eng_00_03),
        ("01-03", eng_01_03),
    ]:
        for r in [0.0064, 0.0065, 0.0066]:
            label = f"BO={label_bo} r={r*100:.2f}%"
            s = bench(label, strategy_params=P6_ANCHOR, **_common(engine, r))
            results.append((label, s))

    # --- C: P6 + sl_lookback=7 × risk (was only at 0.66%) ---
    print("\n--- C: P6 + sl_lookback=7 risk sweep ---")
    for r in [0.0063, 0.0064, 0.0065, 0.0066]:
        label = f"P6 + lb=7 r={r*100:.2f}%"
        s = bench(label, strategy_params=_override(sl_lookback=7),
                  **_common(eng_seed, r))
        results.append((label, s))

    # --- D: combined Asia BO + sl_lookback=7 + risk ---
    print("\n--- D: combined ---")
    for engine_label, eng in [("01-02", eng_01_02), ("23-03", eng_23_03)]:
        for r in [0.0064, 0.0065]:
            label = f"P6 + lb=7 + BO={engine_label} r={r*100:.2f}%"
            s = bench(label, strategy_params=_override(sl_lookback=7),
                      **_common(eng, r))
            results.append((label, s))

    elapsed = time.time() - t0
    print(f"\nTotal: {len(results)} sims in {elapsed:.0f}s")

    # ---- Reports ----
    print()
    print("=" * 110)
    print("★★★ HITS BOTH TARGETS (PnL ≥ $80,565 AND $DD < $2,500)")
    print("=" * 110)
    targets = [(l, s) for l, s in results if s["net_pnl"] >= 80565 and s["max_dd_$"] < 2500]
    if not targets:
        print("  (none — wall still unbroken)")
    else:
        for l, s in sorted(targets, key=lambda x: -x[1]["net_pnl"]):
            print(f"  PnL=${s['net_pnl']:>+7,.0f}  $DD=${s['max_dd_$']:>5,.0f}  "
                  f"P/DD={s['net_pnl']/max(s['max_dd_$'],1):>5.2f}  N={s['trades']:>4}  ← {l}")

    print()
    print("=" * 110)
    print("TOP 25 by PnL with $DD ≤ $2,805 (current WINNER DD)")
    print("=" * 110)
    valid = [(l, s) for l, s in results if s["max_dd_$"] <= 2805 and s["net_pnl"] >= 80565]
    if not valid:
        print("  (no strict Pareto vs current WINNER)")
    for l, s in sorted(valid, key=lambda x: -x[1]["net_pnl"])[:25]:
        print(f"  PnL=${s['net_pnl']:>+7,.0f}  $DD=${s['max_dd_$']:>5,.0f}  "
              f"P/DD={s['net_pnl']/max(s['max_dd_$'],1):>5.2f}  N={s['trades']:>4}  ← {l}")

    print()
    print("=" * 110)
    print("Closest to wall (PnL ≥ $80,565, sorted by DD asc)")
    print("=" * 110)
    pareto = [(l, s) for l, s in results if s["net_pnl"] >= 80565]
    for l, s in sorted(pareto, key=lambda x: x[1]["max_dd_$"])[:15]:
        print(f"  PnL=${s['net_pnl']:>+7,.0f}  $DD=${s['max_dd_$']:>5,.0f}  "
              f"P/DD={s['net_pnl']/max(s['max_dd_$'],1):>5.2f}  N={s['trades']:>4}  ← {l}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
