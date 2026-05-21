"""Phase 9 (v3) — Final Pareto refinement and validation.

Key finding from Phase 8: hard non-monotonicity at risk=0.63% → 0.64%.
- DD < $2,500 caps PnL at ~$76,538 (risk=0.63%) → BELOW user's PnL floor
- Best DD with PnL ≥ $80,565 is $2,877 (risk=0.65%)

So the deliverable becomes the BEST Pareto-strict improvement vs seed.
This phase compiles the top candidates and validates them.
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

SEED_BO = [(9, 0, 10, 0), (13, 0, 14, 30), (17, 0, 23, 59)]
P7_BO   = [(1, 0, 2, 0), (9, 0, 10, 0), (13, 0, 14, 30), (17, 0, 23, 59)]


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
    print("PHASE 9 (v3) — Final Pareto refinement & validation")
    print("Target: maximize PnL with $DD ≤ $2,933 (seed DD), STRICTLY beat seed on both axes")
    print("=" * 110)

    results = []
    t0 = time.time()

    eng_seed_bo = seed_engine()
    eng_01_02 = build_engine(P7_BO)

    # ---- Block A: P6 anchor × {seed-bo, +01-02} × risk {0.63...0.67}
    print("\n--- P6 anchor × blackouts × risk band (fine) ---")
    for label_bo, engine in [("seed-bo", eng_seed_bo), ("01-02", eng_01_02)]:
        for risk in [0.0063, 0.0064, 0.0065, 0.0066, 0.0067]:
            lbl = f"P6 / {label_bo} / r={risk*100:.2f}%"
            s = bench(lbl, strategy_params=P6_ANCHOR, **_common(engine, risk))
            results.append((lbl, s))

    # ---- Block B: pts_sig_extreme=2 sig_ext=50 stack (P5 finding, adds trades)
    print("\n--- pts_sig_extreme=2 sig_ext=50 variants ---")
    sig_params = _override(pts_sig_extreme=2, sig_extreme=50.0)
    for label_bo, engine in [("seed-bo", eng_seed_bo), ("01-02", eng_01_02)]:
        for risk in [0.0064, 0.0065, 0.0066, 0.0067]:
            lbl = f"P6+sig50 / {label_bo} / r={risk*100:.2f}%"
            s = bench(lbl, strategy_params=sig_params, **_common(engine, risk))
            results.append((lbl, s))

    # ---- Block C: alternative interesting stacks at risk=0.65 and 0.66
    print("\n--- mcp=0.35 stack ---")
    mcp_params = _override(max_candle_pct=0.35)
    for label_bo, engine in [("seed-bo", eng_seed_bo), ("01-02", eng_01_02)]:
        for risk in [0.0065, 0.0066]:
            lbl = f"P6+mcp0.35 / {label_bo} / r={risk*100:.2f}%"
            s = bench(lbl, strategy_params=mcp_params, **_common(engine, risk))
            results.append((lbl, s))

    # ---- Block D: combine P6+01-02+sig50+mcp0.35 (kitchen-sink stack)
    print("\n--- kitchen-sink stack at multiple risk ---")
    ks_params = _override(pts_sig_extreme=2, sig_extreme=50.0, max_candle_pct=0.35)
    for label_bo, engine in [("seed-bo", eng_seed_bo), ("01-02", eng_01_02)]:
        for risk in [0.0064, 0.0065, 0.0066]:
            lbl = f"KS / {label_bo} / r={risk*100:.2f}%"
            s = bench(lbl, strategy_params=ks_params, **_common(engine, risk))
            results.append((lbl, s))

    # ---- Block E: stretch-DD alternative — at risk 0.62-0.63%, with all DD-reducing deltas
    print("\n--- stretch (DD < $2,500) variants ---")
    for risk in [0.0061, 0.0062, 0.0063]:
        # P6 + 01-02
        lbl = f"stretch P6/01-02 r={risk*100:.2f}%"
        s = bench(lbl, strategy_params=P6_ANCHOR, **_common(eng_01_02, risk))
        results.append((lbl, s))
        # KS + 01-02
        lbl = f"stretch KS/01-02 r={risk*100:.2f}%"
        s = bench(lbl, strategy_params=ks_params, **_common(eng_01_02, risk))
        results.append((lbl, s))

    elapsed = time.time() - t0
    print(f"\nTotal: {len(results)} sims in {elapsed:.0f}s")

    # ---- Report ----
    print()
    print("=" * 110)
    print("FULL RESULTS — sorted by P/DD ratio (ALL)")
    print("=" * 110)
    for l, s in sorted(results, key=lambda x: -(x[1]["net_pnl"]/max(x[1]["max_dd_$"],1))):
        marker = ""
        if s["net_pnl"] >= 80565 and s["max_dd_$"] <= 2500:
            marker = "  ★★★ HITS BOTH"
        elif s["net_pnl"] >= 80565 and s["max_dd_$"] <= 2933:
            marker = "  ✓ PnL≥seed, DD≤seed"
        elif s["net_pnl"] >= 80565:
            marker = "  ✓ PnL≥seed"
        elif s["max_dd_$"] <= 2500:
            marker = "  ◇ DD≤$2,500"
        print(f"  P/DD={s['net_pnl']/max(s['max_dd_$'],1):>5.2f}  "
              f"PnL=${s['net_pnl']:>+7,.0f}  $DD=${s['max_dd_$']:>5,.0f}  "
              f"N={s['trades']:>4}  WR={s['win_rate']:.1f}%  ← {l}{marker}")

    print()
    print("=" * 110)
    print("WINNER candidates — PnL ≥ $80,565 with lowest DD")
    print("=" * 110)
    pareto = [(l, s) for l, s in results if s["net_pnl"] >= 80565]
    for l, s in sorted(pareto, key=lambda x: x[1]["max_dd_$"])[:15]:
        seed_pnl_d = s["net_pnl"] - 80565
        seed_dd_d = s["max_dd_$"] - 3023
        print(f"  PnL=${s['net_pnl']:>+7,.0f} (Δ{seed_pnl_d:>+7,.0f})  "
              f"$DD=${s['max_dd_$']:>5,.0f} (Δ{seed_dd_d:>+5,.0f})  "
              f"P/DD={s['net_pnl']/max(s['max_dd_$'],1):>5.2f}  ← {l}")

    print()
    print("=" * 110)
    print("STRETCH candidates — DD ≤ $2,500 with highest PnL")
    print("=" * 110)
    stretch = [(l, s) for l, s in results if s["max_dd_$"] <= 2500]
    for l, s in sorted(stretch, key=lambda x: -x[1]["net_pnl"])[:15]:
        print(f"  PnL=${s['net_pnl']:>+7,.0f}  "
              f"$DD=${s['max_dd_$']:>5,.0f}  "
              f"P/DD={s['net_pnl']/max(s['max_dd_$'],1):>5.2f}  ← {l}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
