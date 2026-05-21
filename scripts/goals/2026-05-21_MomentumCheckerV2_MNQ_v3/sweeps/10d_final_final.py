"""Phase 10d (v3) — Final-final: variation tb / sl_lookback on the edge.

Closest miss: sl_max=41 r=0.65% → $80,790 / $2,539 (DD +$39 over)
Want: cut $39+ DD without losing $225 PnL → ~1.5% DD reduction.

Tactic: vary tick_buffer (slight SL distance shift), sl_lookback (different SL location).
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
    print("PHASE 10d (v3) — FINAL FINAL")
    print("Targets: PnL ≥ $80,565 AND $DD < $2,500")
    print("=" * 110)

    results = []
    t0 = time.time()
    eng_seed = seed_engine()
    eng_01_02 = build_engine([(1, 0, 2, 0), (9, 0, 10, 0),
                              (13, 0, 14, 30), (17, 0, 23, 59)])

    # sl_max=41 with tick_buffer variations + risk
    print("\n--- sl_max=41 × tb × risk ---")
    for tb in [1, 3, 4]:
        for r in [0.0064, 0.0065, 0.0066]:
            label = f"sl_max=41 tb={tb} r={r*100:.2f}%"
            s = bench(label, strategy_params=_override(sl_max_points=41.0, tick_buffer=tb),
                      **_common(eng_seed, r))
            results.append((label, s))

    # sl_max=41 + sl_lookback variations
    print("\n--- sl_max=41 + sl_lookback variations ---")
    for lb in [4, 6, 7]:
        for r in [0.0065, 0.0066]:
            label = f"sl_max=41 lb={lb} r={r*100:.2f}%"
            s = bench(label, strategy_params=_override(sl_max_points=41.0, sl_lookback=lb),
                      **_common(eng_seed, r))
            results.append((label, s))

    # sl_max=41 + BO=01-02 + risk
    print("\n--- sl_max=41 + BO=01-02 + higher risk ---")
    for r in [0.0066, 0.0067, 0.0068]:
        label = f"sl_max=41 + BO=01-02 r={r*100:.2f}%"
        s = bench(label, strategy_params=_override(sl_max_points=41.0),
                  **_common(eng_01_02, r))
        results.append((label, s))

    elapsed = time.time() - t0
    print(f"\nTotal: {len(results)} sims in {elapsed:.0f}s")

    print()
    print("=" * 110)
    print("★★★ HITS BOTH TARGETS")
    print("=" * 110)
    targets = [(l, s) for l, s in results if s["net_pnl"] >= 80565 and s["max_dd_$"] < 2500]
    if not targets:
        print("  (none — wall genuinely structural)")
    else:
        for l, s in sorted(targets, key=lambda x: -x[1]["net_pnl"]):
            print(f"  PnL=${s['net_pnl']:>+7,.0f}  $DD=${s['max_dd_$']:>5,.0f}  "
                  f"P/DD={s['net_pnl']/max(s['max_dd_$'],1):>5.2f}  N={s['trades']:>4}  ← {l}")

    print()
    print("=" * 110)
    print("All results sorted by P/DD")
    print("=" * 110)
    for l, s in sorted(results, key=lambda x: -(x[1]["net_pnl"]/max(x[1]["max_dd_$"],1))):
        marker = ""
        if s["net_pnl"] >= 80565 and s["max_dd_$"] < 2500:
            marker = "  ★★★"
        elif s["net_pnl"] >= 80565:
            marker = "  ✓ PnL"
        elif s["max_dd_$"] < 2500:
            marker = "  ◇ DD"
        print(f"  P/DD={s['net_pnl']/max(s['max_dd_$'],1):>5.2f}  "
              f"PnL=${s['net_pnl']:>+7,.0f}  $DD=${s['max_dd_$']:>5,.0f}  "
              f"N={s['trades']:>4}  ← {l}{marker}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
